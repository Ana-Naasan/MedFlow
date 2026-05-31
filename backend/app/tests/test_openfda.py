"""Tests for the OpenFDA connector: real-shaped query/parse paths, caching,
rate limiting, and evidence-snippet generation — all offline via MockTransport.
"""

from __future__ import annotations

import httpx
import pytest

from backend.app.knowledge import openfda
from backend.app.knowledge.openfda import (
    OpenFdaResult,
    _cache,
    _cache_get,
    _cache_key,
    _CacheEntry,
    _drug_filter,
    _drug_metadata,
    _escape_value,
    _first_text,
    _first_text_list,
    lookup_adverse_events,
    lookup_drug,
    lookup_label,
)

_RX = "197885"


# ── Aggregation + snippets (real query/parse paths) ─────────────────────────


class TestAdverseEvents:
    @pytest.mark.asyncio
    async def test_aggregates_total_reactions_and_seriousness(self, mock_openfda: None) -> None:
        result = (await lookup_adverse_events(rxcui=_RX, limit=2))[0]
        assert result.total_events == 10064
        assert result.rxcui == "197885"
        assert result.generic_name == "LISINOPRIL"
        assert result.brand_name == "PRINIVIL"
        # real reaction frequencies (count= aggregation), ordered by count
        assert result.reaction_counts[0] == ("COUGH", 12000)
        assert result.serious_reactions == ["COUGH", "DIZZINESS", "ANGIOEDEMA"]
        # real per-seriousness counts (one filtered query each → meta.results.total)
        assert result.event_count_by_seriousness == {
            "death": 42,
            "hospitalization": 500,
            "serious": 1000,
        }

    @pytest.mark.asyncio
    async def test_snippets_use_real_counts(self, mock_openfda: None) -> None:
        result = (await lookup_adverse_events(rxcui=_RX, limit=2))[0]
        joined = " ".join(s.label for s in result.evidence_snippets)
        assert "10,064 adverse events reported" in joined
        assert "COUGH (12,000)" in joined  # frequency, not name length
        assert "42 reported events involved death" in joined
        assert "500 reported events involved hospitalisation" in joined
        for s in result.evidence_snippets:
            assert s.id.startswith("openfda:")
            assert s.kind == "openfda_adverse_event"

    @pytest.mark.asyncio
    async def test_stable_ids(self, mock_openfda: None) -> None:
        a = (await lookup_adverse_events(rxcui=_RX, limit=2))[0].evidence_snippets[0]
        b = (await lookup_adverse_events(rxcui=_RX, limit=2))[0].evidence_snippets[0]
        assert a.id == b.id

    @pytest.mark.asyncio
    async def test_generic_name_path(self, mock_openfda: None) -> None:
        result = await lookup_adverse_events(generic_name="lisinopril", limit=2)
        assert result and result[0].total_events == 10064

    @pytest.mark.asyncio
    async def test_empty_when_no_data(self, mock_openfda_factory) -> None:
        def empty(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"meta": {"results": {"total": 0}}, "results": []})

        mock_openfda_factory(empty)
        assert await lookup_adverse_events(rxcui="0000") == []


class TestLabel:
    @pytest.mark.asyncio
    async def test_label_sections_to_snippets(self, mock_openfda: None) -> None:
        result = (await lookup_label(rxcui=_RX, limit=1))[0]
        assert result.boxed_warnings and result.warnings and result.contraindications
        kinds = {s.kind for s in result.evidence_snippets}
        assert kinds == {"openfda_label"}
        joined = " ".join(s.label for s in result.evidence_snippets)
        assert "BOXED WARNING:" in joined
        assert "WARNING:" in joined
        assert "Contraindication:" in joined
        assert "Adverse reactions (from label):" in joined

    @pytest.mark.asyncio
    async def test_label_generic_name_path(self, mock_openfda: None) -> None:
        result = await lookup_label(generic_name="lisinopril", limit=1)
        # generic_name echoes the caller's value; the record still resolves.
        assert result and result[0].generic_name == "lisinopril"
        assert result[0].boxed_warnings


class TestLookupDrug:
    @pytest.mark.asyncio
    async def test_merges_event_and_label(self, mock_openfda: None) -> None:
        result = await lookup_drug(rxcui=_RX)
        assert result is not None
        kinds = {s.kind for s in result.evidence_snippets}
        assert {"openfda_adverse_event", "openfda_label"} <= kinds
        assert result.boxed_warnings  # label data merged in

    @pytest.mark.asyncio
    async def test_both_fail_returns_none(self) -> None:
        err = httpx.HTTPStatusError("x", request=None, response=None)
        with pytest.MonkeyPatch().context() as mp:

            async def boom(**_):
                raise err

            mp.setattr(openfda, "lookup_adverse_events", boom)
            mp.setattr(openfda, "lookup_label", boom)
            assert await lookup_drug(rxcui=_RX) is None

    @pytest.mark.asyncio
    async def test_label_only_when_event_fails(self, mock_openfda: None) -> None:
        err = httpx.HTTPStatusError("x", request=None, response=None)
        with pytest.MonkeyPatch().context() as mp:

            async def boom(**_):
                raise err

            mp.setattr(openfda, "lookup_adverse_events", boom)
            result = await lookup_drug(rxcui=_RX)
            assert result is not None
            assert result.boxed_warnings
            assert result.evidence_snippets[0].kind == "openfda_label"

    @pytest.mark.asyncio
    async def test_event_only_when_label_fails(self, mock_openfda: None) -> None:
        err = httpx.HTTPStatusError("x", request=None, response=None)
        with pytest.MonkeyPatch().context() as mp:

            async def boom(**_):
                raise err

            mp.setattr(openfda, "lookup_label", boom)
            result = await lookup_drug(rxcui=_RX)
            assert result is not None
            assert result.total_events == 10064
            assert not result.boxed_warnings

    @pytest.mark.asyncio
    async def test_fills_names_from_label_when_event_blank(self, mock_openfda: None) -> None:
        with pytest.MonkeyPatch().context() as mp:

            async def blank_events(**_):
                return [OpenFdaResult(rxcui=_RX, total_events=5)]

            mp.setattr(openfda, "lookup_adverse_events", blank_events)
            result = await lookup_drug(rxcui=_RX)
            assert result is not None
            assert result.generic_name == "LISINOPRIL"
            assert result.brand_name == "PRINIVIL"
            assert result.manufacturer == "Merck"


# ── Guards ──────────────────────────────────────────────────────────────────


class TestGuards:
    @pytest.mark.asyncio
    async def test_value_error_without_identifier(self) -> None:
        for fn in (lookup_adverse_events, lookup_label, lookup_drug):
            with pytest.raises(ValueError, match="Provide either"):
                await fn()

    def test_drug_filter_raises(self) -> None:
        with pytest.raises(ValueError, match="Provide either"):
            _drug_filter("openfda", None, None)


# ── Caching + rate limiting + HTTP ──────────────────────────────────────────


class TestTransport:
    @pytest.mark.asyncio
    async def test_seriousness_query_uses_real_and_operator(self, mock_openfda_factory) -> None:
        # The wire URL must carry the real "+AND+" delimiter (space-encoded),
        # NOT a percent-encoded literal "%2BAND%2B" — otherwise openFDA parses
        # one broken term and the seriousness counts are wrong/absent.
        seen: list[str] = []

        def capture(request: httpx.Request) -> httpx.Response:
            seen.append(str(request.url))
            from backend.app.tests.conftest import _route

            params = request.url.params
            body = _route(
                params.get("search", ""),
                params.get("count"),
                request.url.path.endswith("/label.json"),
            )
            return httpx.Response(200, json=body)

        mock_openfda_factory(capture)
        await lookup_adverse_events(rxcui=_RX, limit=2)
        seriousness_urls = [u for u in seen if "seriousnessdeath" in u]
        assert seriousness_urls, "no seriousness query was issued"
        for u in seriousness_urls:
            assert "+AND+" in u  # real Lucene operator
            assert "%2BAND%2B" not in u  # not the broken literal-plus form

    @pytest.mark.asyncio
    async def test_cache_hit_avoids_second_fetch(self, mock_openfda_factory) -> None:
        calls = {"n": 0}

        def counting(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            params = request.url.params
            from backend.app.tests.conftest import _route

            body = _route(
                params.get("search", ""),
                params.get("count"),
                request.url.path.endswith("/label.json"),
            )
            return httpx.Response(200, json=body)

        mock_openfda_factory(counting)
        await lookup_adverse_events(rxcui=_RX, limit=2)
        first = calls["n"]
        assert first == 5  # main + count + 3 seriousness queries
        await lookup_adverse_events(rxcui=_RX, limit=2)
        assert calls["n"] == first  # all served from cache the second time

    @pytest.mark.asyncio
    async def test_retries_once_on_429(self, mock_openfda_factory, monkeypatch) -> None:
        state = {"hits": 0}

        def flaky(request: httpx.Request) -> httpx.Response:
            state["hits"] += 1
            if state["hits"] == 1:
                return httpx.Response(429, headers={"Retry-After": "1"})
            return httpx.Response(200, json={"meta": {"results": {"total": 7}}, "results": [{}]})

        sleeps: list[float] = []

        async def fake_sleep(secs: float) -> None:
            sleeps.append(secs)

        monkeypatch.setattr(openfda.asyncio, "sleep", fake_sleep)
        mock_openfda_factory(flaky)
        body = await openfda._get_json("event", {"search": "x", "limit": 1})
        assert body["meta"]["results"]["total"] == 7
        assert state["hits"] == 2  # one 429 + one success
        assert sleeps == [1]

    @pytest.mark.asyncio
    async def test_raise_for_status_propagates(self, mock_openfda_factory) -> None:
        def boom(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "x"})

        mock_openfda_factory(boom)
        with pytest.raises(httpx.HTTPStatusError):
            await openfda._get_json("event", {"search": "x", "limit": 1})

    def test_client_includes_api_key(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENFDA_API_KEY", "k-123")
        c = openfda._client()
        assert c.params.get("api_key") == "k-123"

    def test_client_without_api_key(self, monkeypatch) -> None:
        monkeypatch.delenv("OPENFDA_API_KEY", raising=False)
        assert "api_key" not in openfda._client().params


class TestCache:
    def test_cache_get_expired(self) -> None:
        # monotonic() has an arbitrary epoch, so derive a genuinely-past stamp
        # rather than a hardcoded constant (which isn't "old" on a fresh CI box).
        stale = openfda.time.monotonic() - openfda._CACHE_TTL - 1
        _cache["k"] = _CacheEntry(data={"x": 1}, fetched_at=stale)
        assert _cache_get("k") is None
        assert "k" not in _cache

    def test_cache_get_missing(self) -> None:
        assert _cache_get("nope") is None

    def test_cache_evicts_oldest_over_max(self) -> None:
        for i in range(openfda._CACHE_MAX_SIZE + 5):
            openfda._cache_set(f"key-{i}", {"i": i})
        assert len(_cache) == openfda._CACHE_MAX_SIZE
        assert "key-0" not in _cache  # oldest evicted
        assert f"key-{openfda._CACHE_MAX_SIZE + 4}" in _cache

    def test_cache_key_order_independent(self) -> None:
        a = _cache_key("event", {"search": "x", "limit": 1})
        b = _cache_key("event", {"limit": 1, "search": "x"})
        assert a == b


class TestTokenBucket:
    @pytest.mark.asyncio
    async def test_acquire_with_tokens_does_not_sleep(self, monkeypatch) -> None:
        slept: list[float] = []

        async def fake_sleep(s: float) -> None:
            slept.append(s)

        monkeypatch.setattr(openfda.asyncio, "sleep", fake_sleep)
        openfda._bucket._tokens = 5.0
        await openfda._bucket.acquire()
        assert slept == []

    @pytest.mark.asyncio
    async def test_acquire_when_empty_sleeps(self, monkeypatch) -> None:
        slept: list[float] = []

        async def fake_sleep(s: float) -> None:
            slept.append(s)

        monkeypatch.setattr(openfda.asyncio, "sleep", fake_sleep)
        openfda._bucket._tokens = 0.0
        openfda._bucket._last = openfda.time.monotonic()
        await openfda._bucket.acquire()
        assert slept and slept[0] > 0


# ── Pure helpers ──────────────────────────────────────────────────────────


class TestHelpers:
    def test_escape_value_always_quotes(self) -> None:
        assert _escape_value("aspirin") == '"aspirin"'
        assert _escape_value("atorvastatin calcium") == '"atorvastatin calcium"'

    def test_escape_value_escapes_quote_and_backslash(self) -> None:
        assert _escape_value('a"b') == '"a\\"b"'
        assert _escape_value("a\\b") == '"a\\\\b"'

    def test_escape_value_neutralises_lucene_injection(self) -> None:
        # A whitespace-free metacharacter payload must NOT survive as bare
        # operators — it is contained inside the quoted phrase.
        out = _escape_value("foo) OR (seriousnessdeath:1")
        assert out.startswith('"') and out.endswith('"')
        assert _escape_value("a+AND+b") == '"a+AND+b"'  # operators are literal inside quotes

    def test_drug_filter_quotes_values(self) -> None:
        assert _drug_filter("openfda", "197885", None) == 'openfda.rxcui:"197885"'
        assert _drug_filter("openfda", None, "lisinopril") == 'openfda.generic_name:"lisinopril"'

    def test_first_text_unwraps_final_list(self) -> None:
        assert _first_text({"a": ["x"]}, "a") == "x"

    def test_first_text_unwraps_mid_path_list(self) -> None:
        # A mid-path list is unwrapped to its first item, consuming the path key;
        # the remaining dict is then stringified (documents existing behaviour).
        assert _first_text({"a": [{"b": "x"}]}, "a", "b") == "{'b': 'x'}"

    def test_first_text_empty_list(self) -> None:
        assert _first_text({"a": []}, "a") is None
        assert _first_text({"a": []}, "a", "b") is None

    def test_first_text_non_dict_mid_path(self) -> None:
        assert _first_text({"a": "s"}, "a", "b") is None

    def test_first_text_list_non_dict_mid_path(self) -> None:
        assert _first_text_list({"a": "s"}, "a", "b") == []

    def test_first_text_list_empty_path_value(self) -> None:
        assert _first_text_list({}, "x") == []

    def test_first_text_list_mid_list(self) -> None:
        assert _first_text_list({"a": []}, "a", "b") == []

    def test_drug_metadata_matches_rxcui(self) -> None:
        results = [
            {"patient": {"drug": [{"openfda": {"rxcui": ["197885"], "generic_name": ["X"]}}]}}
        ]
        assert _drug_metadata(results, "197885", None)["generic_name"] == ["X"]

    def test_drug_metadata_matches_generic(self) -> None:
        results = [{"patient": {"drug": [{"openfda": {"generic_name": ["LISINOPRIL"]}}]}}]
        assert _drug_metadata(results, None, "lisinopril")["generic_name"] == ["LISINOPRIL"]

    def test_drug_metadata_falls_back_to_first_openfda(self) -> None:
        results = [{"patient": {"drug": [{"openfda": {"brand_name": ["B"]}}]}}]
        assert _drug_metadata(results, "999", None)["brand_name"] == ["B"]

    def test_drug_metadata_empty_when_no_openfda(self) -> None:
        assert _drug_metadata([{"patient": {"drug": [{}]}}], "1", None) == {}

    def test_serious_reactions_property_orders_by_count(self) -> None:
        r = OpenFdaResult(reaction_counts=[("A", 5), ("B", 3)])
        assert r.serious_reactions == ["A", "B"]
