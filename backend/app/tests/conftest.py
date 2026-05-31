"""Shared fixtures and configuration for all backend tests."""

import json
from pathlib import Path
from typing import Any

import pytest

from backend.app.knowledge.openfda import _cache_key, _CacheEntry, _cache

FIXTURE_DIR = Path(__file__).parent / "fixtures"

# Cache keys used by the fixtures
_EVENT_KEY = _cache_key("event", "patient.drug.openfda.rxcui:197885", 2)
_LABEL_KEY = _cache_key("label", "openfda.rxcui:197885", 1)


def _load_fixture(basename: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / basename).read_text(encoding="utf-8"))


# ── Module-level autouse: clear cache before every test ────────────────────


@pytest.fixture(autouse=True)
def _clear_openfda_cache() -> None:
    _cache.clear()


# ── Fixture data loaders (no side effects on _cache) ───────────────────────


@pytest.fixture
def openfda_event_197885_data() -> dict[str, Any]:
    """Raw captured event response for RxCUI 197885 (lisinopril), limit=2."""
    return _load_fixture("openfda_event_197885.json")


@pytest.fixture
def openfda_event_197885_serious_data() -> dict[str, Any]:
    """Synthetic event fixture with death/hospitalization data for coverage."""
    return _load_fixture("openfda_event_197885_serious.json")


@pytest.fixture
def openfda_label_197885_data() -> dict[str, Any]:
    """Raw captured label response for RxCUI 197885 (lisinopril), limit=1."""
    return _load_fixture("openfda_label_197885.json")


# ── Fixtures that pre-populate the module cache ────────────────────────────


@pytest.fixture
def cached_event_197885(
    openfda_event_197885_data: dict[str, Any],
) -> None:
    """Pre-populate the OpenFDA cache for the event endpoint (limit=2).

    After this fixture, ``lookup_adverse_events(rxcui='197885', limit=2)``
    returns fixture data without a network call.
    """
    _cache[_EVENT_KEY] = _CacheEntry(
        data=openfda_event_197885_data, fetched_at=999999999.0
    )


@pytest.fixture
def cached_label_197885(
    openfda_label_197885_data: dict[str, Any],
) -> None:
    """Pre-populate the OpenFDA cache for the label endpoint (limit=1, by rxcui)."""
    _cache[_LABEL_KEY] = _CacheEntry(
        data=openfda_label_197885_data, fetched_at=999999999.0
    )


@pytest.fixture
def cached_event_197885_serious(
    openfda_event_197885_serious_data: dict[str, Any],
) -> None:
    """Pre-populate cache with the serious-event fixture."""
    _cache[_EVENT_KEY] = _CacheEntry(
        data=openfda_event_197885_serious_data, fetched_at=999999999.0
    )


@pytest.fixture
def cached_openfda_all(
    cached_event_197885: None,
    cached_label_197885: None,
) -> None:
    """Pre-populate both event and label caches."""
