"""Tests for OpenFDA caching, evidence-snippet generation, and offline fixtures.

Offline (default)
-----------------
These tests use pre-captured JSON fixtures and never hit the network.
They run on every ``pytest`` invocation.

Live (``--live``)
-----------------
Tests that hit the real OpenFDA API are skipped by default.
Run them with ``pytest --live`` when you have internet access.
"""

import asyncio
import time
from unittest.mock import patch

import httpx
import pytest

from backend.app.knowledge.openfda import (
    _bucket,
    _cache,
    _cache_get,
    _cache_key,
    _CacheEntry,
    _first_text,
    _first_text_list,
    lookup_adverse_events,
    lookup_label,
)

from backend.app.fhir.subset import _is_mrn_identifier as _is_mrn


# ── Offline tests (use fixtures, no network) ───────────────────────────────


class TestOffline:
    """Run against pre-captured fixtures — zero network required."""

    @pytest.mark.asyncio
    async def test_cached_call_is_instant(self, cached_openfda_all: None) -> None:
        t0 = time.monotonic()
        results = await lookup_adverse_events(rxcui="197885", limit=2)
        assert time.monotonic() - t0 < 0.005
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_cache_independent(self, cached_openfda_all: None) -> None:
        t0 = time.monotonic()
        await lookup_adverse_events(rxcui="197885", limit=2)
        await lookup_label(rxcui="197885", limit=1)
        assert time.monotonic() - t0 < 0.010

    @pytest.mark.asyncio
    async def test_evidence_snippets_present(self, cached_openfda_all: None) -> None:
        results = await lookup_adverse_events(rxcui="197885", limit=2)
        r = results[0]
        assert len(r.evidence_snippets) > 0
        s = r.evidence_snippets[0]
        assert s.id.startswith("openfda:")
        assert s.kind == "openfda_adverse_event"
        assert "reported" in s.label.lower()
        # stable IDs
        s2 = (await lookup_adverse_events(rxcui="197885", limit=2))[0].evidence_snippets[0]
        assert s.id == s2.id

    @pytest.mark.asyncio
    async def test_label_snippets(self, cached_openfda_all: None) -> None:
        results = await lookup_label(rxcui="197885", limit=1)
        r = results[0]
        assert len(r.evidence_snippets) > 0
        assert r.evidence_snippets[0].kind == "openfda_label"

    @pytest.mark.asyncio
    async def test_lookup_drug_merges_snippets(self, cached_openfda_all: None) -> None:
        from backend.app.knowledge.openfda import lookup_drug
        result = await lookup_drug(rxcui="197885")
        assert result is not None
        kinds = {s.kind for s in result.evidence_snippets}
        assert "openfda_adverse_event" in kinds
        assert "openfda_label" in kinds


class TestEdgeCases:
    """ValueError guards, token bucket, cache TTL, _first_text, API key, etc."""

    # ── ValueError guards ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_raises_on_no_args(self) -> None:
        for fn in [lookup_adverse_events, lookup_label]:
            with pytest.raises(ValueError, match="Provide either"):
                await fn()
        from backend.app.knowledge.openfda import lookup_drug
        with pytest.raises(ValueError, match="Provide either"):
            await lookup_drug()

    # ── Token bucket ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_token_bucket_acquire_when_empty(self) -> None:
        """Drain the bucket so a token must be replenished first."""
        burst = _bucket._burst
        for _ in range(burst):
            await _bucket.acquire()
        # The bucket is now empty — the next acquire should sleep briefly
        t0 = time.monotonic()
        await _bucket.acquire()
        dt = time.monotonic() - t0
        assert dt > 0, "Bucket was empty; acquire should have waited"

    @pytest.mark.asyncio
    async def test_token_bucket_acquire_when_idle(self) -> None:
        """After waiting, the bucket should have replenished tokens."""
        # Ensure bucket is empty
        for _ in range(_bucket._burst + 1):
            await _bucket.acquire()
        # Sleep long enough for at least one token
        await asyncio.sleep(60.0 / 200 + 0.01)
        t0 = time.monotonic()
        await _bucket.acquire()
        assert time.monotonic() - t0 < 0.05

    # ── Cache TTL ──────────────────────────────────────────────────────

    def test_cache_get_expired_entry(self) -> None:
        """Entries past TTL are evicted and return None."""
        key = "test_expired"
        very_old = 42.0  # well before now
        _cache[key] = _CacheEntry(data={"x": 1}, fetched_at=very_old)
        assert _cache_get(key) is None
        assert key not in _cache

    def test_cache_get_missing_key(self) -> None:
        assert _cache_get("nope") is None

    # ── _first_text edge cases ─────────────────────────────────────────

    def test_first_text_handles_final_list(self) -> None:
        """When the final value is a list, unwrap to first element."""
        assert _first_text({"a": ["x"]}, "a") == "x"

    def test_first_text_empty_list(self) -> None:
        assert _first_text({"a": []}, "a") is None
        assert _first_text({"a": []}, "a", "b") is None

    def test_first_text_non_dict_mid_path(self) -> None:
        assert _first_text({"a": "string"}, "a", "b") is None

    def test_first_text_list_non_dict_mid_path(self) -> None:
        assert _first_text_list({"a": "string"}, "a", "b") == []

    def test_first_text_list_empty_path(self) -> None:
        assert _first_text_list({}, "x") == []

    def test_first_text_handles_list_with_elements(self) -> None:
        """When an intermediate path element is a list, unwrap to first item."""
        result = _first_text({"a": [{"b": "x"}]}, "a", "b")
        # After a→list→first dict, b key resolves to 'x', wrapped via str()
        assert result == "{'b': 'x'}"

    def test_first_text_list_mid_path_list(self) -> None:
        """When mid-path element is a list, grab first item."""
        # _first_text_list converts non-string items to their repr, so {'b':'c'} → "{'b': 'c'}"
        result = _first_text_list({"a": [{"b": "c"}]}, "a", "b")
        assert len(result) == 1
        assert "c" in result[0]

    def test_first_text_list_empty_list_path(self) -> None:
        """When mid-path element is an empty list, return []."""
        assert _first_text_list({"a": []}, "a", "b") == []

    # ── _is_mrn_identifier edge cases ──────────────────────────────────

    def test_is_mrn_not_a_dict(self) -> None:
        assert _is_mrn("not-a-dict") is False

    def test_is_mrn_no_type(self) -> None:
        assert _is_mrn({"value": "x"}) is False

    def test_is_mrn_type_no_coding(self) -> None:
        assert _is_mrn({"value": "x", "type": {}}) is False

    def test_is_mrn_coding_not_list(self) -> None:
        assert _is_mrn({"value": "x", "type": {"coding": "not-list"}}) is False

    # ── API key branch ─────────────────────────────────────────────────

    def test_api_key_in_client(self) -> None:
        from backend.app.knowledge.openfda import _client
        with patch.dict("os.environ", {"OPENFDA_API_KEY": "test-key-123"}):
            c = _client()
            assert "api_key" in c.params
            assert c.params["api_key"] == "test-key-123"

    def test_no_api_key_in_client(self) -> None:
        from backend.app.knowledge.openfda import _client
        with patch.dict("os.environ", {}, clear=True):
            c = _client()
            assert "api_key" not in c.params

    # ── lookup_drug HTTP error handling ────────────────────────────────

    @pytest.mark.asyncio
    async def test_lookup_drug_both_fail(self) -> None:
        """When both event and label raise HTTP errors, lookup_drug returns None."""
        from backend.app.knowledge.openfda import lookup_drug
        with patch(
            "backend.app.knowledge.openfda.lookup_adverse_events",
            side_effect=httpx.HTTPStatusError("err", request=None, response=None),
        ):
            with patch(
                "backend.app.knowledge.openfda.lookup_label",
                side_effect=httpx.HTTPStatusError("err", request=None, response=None),
            ):
                result = await lookup_drug(rxcui="any")
                assert result is None

    @pytest.mark.asyncio
    async def test_lookup_drug_event_fails_label_succeeds(
        self, cached_label_197885: None
    ) -> None:
        """When event fails but label is cached, label data is returned."""
        from backend.app.knowledge.openfda import lookup_drug
        with patch(
            "backend.app.knowledge.openfda.lookup_adverse_events",
            side_effect=httpx.HTTPStatusError("err", request=None, response=None),
        ):
            result = await lookup_drug(rxcui="197885")
            assert result is not None
            assert result.evidence_snippets[0].kind == "openfda_label"

    # ── Generic name search path ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_lookup_by_generic_name_event(self) -> None:
        """lookup_adverse_events with generic_name uses the other search path."""
        import json
        from pathlib import Path
        key = _cache_key("event", 'patient.drug.openfda.generic_name:"lisinopril"', 1)
        _cache[key] = _CacheEntry(
            data=json.loads(Path("backend/app/tests/fixtures/openfda_event_197885.json").read_text()),
            fetched_at=999999999.0,
        )
        results = await lookup_adverse_events(generic_name="lisinopril", limit=1)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_lookup_by_generic_name_label(self) -> None:
        """lookup_label with generic_name uses the other search path."""
        import json
        from pathlib import Path
        key = _cache_key("label", 'openfda.generic_name:"lisinopril"', 1)
        _cache[key] = _CacheEntry(
            data=json.loads(Path("backend/app/tests/fixtures/openfda_label_197885.json").read_text()),
            fetched_at=999999999.0,
        )
        results = await lookup_label(generic_name="lisinopril", limit=1)
        assert len(results) > 0

    # ── lookup_drug merge branches (event has empty name, label fills) ─

    @pytest.mark.asyncio
    async def test_lookup_drug_merge_names(self, cached_openfda_all: None) -> None:
        """lookup_drug merge fills names from label when event is missing them."""
        from backend.app.knowledge.openfda import lookup_drug
        result = await lookup_drug(rxcui="197885")
        assert result is not None
        assert result.generic_name is not None

    @pytest.mark.asyncio
    async def test_lookup_drug_fills_names_from_label(self, cached_label_197885: None) -> None:
        """When event returns empty names, label fills generic_name/brand_name/manufacturer."""
        from backend.app.knowledge.openfda import lookup_drug, OpenFdaResult
        from backend.app.knowledge.openfda import lookup_adverse_events as real_lookup_events

        async def patched_events(**kwargs) -> list:
            """Return a result with no generic_name, brand_name, or manufacturer."""
            r = OpenFdaResult(rxcui="197885", total_events=100)
            r.evidence_snippets = []
            return [r]

        with patch(
            "backend.app.knowledge.openfda.lookup_adverse_events",
            patched_events,
        ):
            result = await lookup_drug(rxcui="197885")
            assert result is not None
            assert result.generic_name == "LISINOPRIL AND HYDROCHLOROTHIAZIDE TABLETS"
            assert result.brand_name == "Lisinopril and Hydrochlorothiazide"
            assert result.manufacturer is not None

    @pytest.mark.asyncio
    async def test_lookup_drug_returns_label_only_when_event_absent(self, cached_label_197885: None) -> None:
        """When events fail but label succeeds, return label data (line 569-570)."""
        from backend.app.knowledge.openfda import lookup_drug
        with patch(
            "backend.app.knowledge.openfda.lookup_adverse_events",
            side_effect=httpx.HTTPStatusError("err", request=None, response=None),
        ):
            result = await lookup_drug(rxcui="197885")
            assert result is not None
            assert result.generic_name is not None
            assert result.evidence_snippets[0].kind == "openfda_label"

    # ── Generic name search triggering candidate match (lines 428-429) ─

    @pytest.mark.asyncio
    async def test_event_generic_name_candidate_match(self) -> None:
        """When search is by generic_name, the candidate match branch fires."""
        import json
        from pathlib import Path

        # Use fixture where drugs match by generic_name
        key = _cache_key("event", 'patient.drug.openfda.generic_name:"lisinopril"', 2)
        _cache[key] = _CacheEntry(
            data=json.loads(Path("backend/app/tests/fixtures/openfda_event_197885_match_generic.json").read_text()),
            fetched_at=999999999.0,
        )
        results = await lookup_adverse_events(generic_name="lisinopril", limit=2)
        assert len(results) > 0
        assert results[0].brand_name is not None

    # ── Seriousness snippets ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_seriousness_snippets(self, cached_event_197885_serious: None) -> None:
        results = await lookup_adverse_events(rxcui="197885", limit=2)
        labels = " ".join(s.label for s in results[0].evidence_snippets)
        assert "death" in labels
        assert "hospitalisation" in labels


# ── Live tests (hit the real API) ──────────────────────────────────────────


@pytest.mark.live
class TestLive:
    @pytest.mark.asyncio
    async def test_cache_10x(self) -> None:
        rxcui, limit = "197885", 2
        t0 = time.monotonic()
        first = await lookup_adverse_events(rxcui=rxcui, limit=limit)
        t1 = time.monotonic()
        t2 = time.monotonic()
        second = await lookup_adverse_events(rxcui=rxcui, limit=limit)
        t3 = time.monotonic()
        ratio = (t1 - t0) / max(t3 - t2, 1e-9)
        assert ratio >= 10
        assert first[0].total_events > 0
        assert second[0].total_events > 0

    @pytest.mark.asyncio
    async def test_live_snippets(self) -> None:
        r = (await lookup_adverse_events(rxcui="197885", limit=1))[0]
        assert len(r.evidence_snippets) > 0
