"""OpenFDA adverse-event and drug-label lookups with rate limiting, caching,
and evidence-snippet extraction.

Rate limits
-----------
OpenFDA allows up to **240 requests per minute** with an API key
(``OPENFDA_API_KEY`` env var).  Without a key the limit is lower and
you may receive ``429 Too Many Requests``.  This module implements
an in-memory token-bucket so we never exceed 200 req/min, leaving
headroom for concurrent callers.

Cache
-----
Responses are cached in an ``<OpenFDAQuery.__hash__> → _CacheEntry``
dict with a default TTL of **1 hour**.  The cache is process-local
and is invalidated on restart.

Evidence snippets
-----------------
Each public function returns ``list[OpenFdaResult]`` whose
``evidence_snippets`` field contains human-readable bullet points
suitable for inclusion in a ``DecisionPacket`` or citation list.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from hashlib import md5
from typing import Any

import httpx

BASE_URL = "https://api.fda.gov/drug"

# Each "token" represents one allowed request.  We refill at a rate
# that stays comfortably below the 240 req/min cap.
_RATE_LIMIT_RATE = 200  # tokens per minute
_RATE_LIMIT_BURST = 20  # max burst size
_CACHE_TTL = 3600  # seconds (1 hour)

# ── Data containers ────────────────────────────────────────────────────────


@dataclass
class EvidenceSnippet:
    """A single piece of evidence with a stable, reproducible ID.

    The ``id`` field is computed deterministically from the source,
    the drug identifier, and the snippet type, so the same snippet
    always gets the same ID across pipeline runs.

    ``label`` is the human-readable text (e.g. a bullet point).
    ``ref`` and ``kind`` mirror the ``Citation`` DTO fields for
    easy conversion.
    """

    id: str
    kind: str  # e.g. "openfda_adverse_event", "openfda_label"
    ref: str  # resolvable citation target
    label: str  # human-readable evidence text


@dataclass
class OpenFdaResult:
    """Normalised representation of OpenFDA data for one drug."""

    rxcui: str | None = None
    generic_name: str | None = None
    brand_name: str | None = None
    manufacturer: str | None = None

    # Adverse reactions (from /event)
    serious_reactions: list[str] = field(default_factory=list)
    total_events: int = 0
    event_count_by_seriousness: dict[str, int] = field(default_factory=dict)

    # Label snippets (from /label)
    indications: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    contraindications: list[str] = field(default_factory=list)
    adverse_reactions_label: list[str] = field(default_factory=list)
    boxed_warnings: list[str] = field(default_factory=list)

    # Evidence snippets with stable IDs, suitable for citations
    evidence_snippets: list[EvidenceSnippet] = field(default_factory=list)

    raw_event: dict[str, Any] | None = None
    raw_label: dict[str, Any] | None = None


# ── Token-bucket rate limiter ──────────────────────────────────────────────


class _TokenBucket:
    """Simple in-process token-bucket rate limiter."""

    def __init__(self, rate: float, burst: int) -> None:
        self._rate = rate / 60.0  # tokens per second
        self._burst = burst
        self._tokens = float(burst)
        self._last = time.monotonic()

    async def acquire(self) -> None:
        """Wait until a token is available (non-blocking if tokens remain)."""
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return

        deficit = 1.0 - self._tokens
        wait = deficit / self._rate
        self._tokens = 0.0
        self._last = now + wait
        await asyncio.sleep(wait)


_bucket = _TokenBucket(rate=_RATE_LIMIT_RATE, burst=_RATE_LIMIT_BURST)

# ── Cache ──────────────────────────────────────────────────────────────────


@dataclass
class _CacheEntry:
    data: dict[str, Any]  # full response body
    fetched_at: float


_cache: dict[str, _CacheEntry] = {}


def _cache_key(endpoint: str, search: str, limit: int) -> str:
    raw = f"{endpoint}|{search}|{limit}"
    return md5(raw.encode()).hexdigest()


def _cache_get(key: str) -> dict[str, Any] | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    if time.monotonic() - entry.fetched_at > _CACHE_TTL:
        del _cache[key]
        return None
    return entry.data


def _cache_set(key: str, data: dict[str, Any]) -> None:
    _cache[key] = _CacheEntry(data=data, fetched_at=time.monotonic())


# ── Evidence snippets ──────────────────────────────────────────────────────


def _stable_id(drug_ref: str, *parts: str) -> str:
    """Build a deterministic, stable ID for an evidence snippet.

    Example
    -------
    >>> _stable_id("197885", "adverse_events", "total_count")
    'openfda:197885:adverse_events:total_count'
    """
    safe = drug_ref.replace(" ", "_").lower() if drug_ref else "unknown"
    return "openfda:" + ":".join([safe, *parts])


def _build_snippets(
    result: OpenFdaResult,
    source: str,  # "adverse_events" | "label"
) -> list[EvidenceSnippet]:
    """Return evidence bullet points with stable IDs from a result."""
    snippets: list[EvidenceSnippet] = []
    drug_ref = result.rxcui or result.generic_name or ""
    drug_label = result.generic_name or result.brand_name or result.rxcui or "this drug"

    if source == "adverse_events":
        if result.total_events:
            snippets.append(EvidenceSnippet(
                id=_stable_id(drug_ref, "adverse_events", "total_count"),
                kind="openfda_adverse_event",
                ref=f"openfda:adverse_events:{drug_ref}:total_count",
                label=(
                    f"{result.total_events:,} adverse events reported "
                    f"for {drug_label}."
                ),
            ))
        if result.serious_reactions:
            top = result.serious_reactions[:5]
            snippets.append(EvidenceSnippet(
                id=_stable_id(drug_ref, "adverse_events", "top_reactions"),
                kind="openfda_adverse_event",
                ref=f"openfda:adverse_events:{drug_ref}:top_reactions",
                label=f"Most-reported reactions: {', '.join(top)}.",
            ))
        if result.event_count_by_seriousness.get("death"):
            snippets.append(EvidenceSnippet(
                id=_stable_id(drug_ref, "adverse_events", "death_count"),
                kind="openfda_adverse_event",
                ref=f"openfda:adverse_events:{drug_ref}:death_count",
                label=(
                    f"{result.event_count_by_seriousness['death']} events "
                    "involved death."
                ),
            ))
        if result.event_count_by_seriousness.get("hospitalization"):
            snippets.append(EvidenceSnippet(
                id=_stable_id(drug_ref, "adverse_events", "hospitalization_count"),
                kind="openfda_adverse_event",
                ref=f"openfda:adverse_events:{drug_ref}:hospitalization_count",
                label=(
                    f"{result.event_count_by_seriousness['hospitalization']} events "
                    "involved hospitalisation."
                ),
            ))

    if source == "label":
        if result.boxed_warnings:
            snippets.append(EvidenceSnippet(
                id=_stable_id(drug_ref, "label", "boxed_warning"),
                kind="openfda_label",
                ref=f"openfda:label:{drug_ref}:boxed_warning",
                label=f"BOXED WARNING: {result.boxed_warnings[0][:200]}",
            ))
        if result.warnings:
            snippets.append(EvidenceSnippet(
                id=_stable_id(drug_ref, "label", "warning"),
                kind="openfda_label",
                ref=f"openfda:label:{drug_ref}:warning",
                label=f"WARNING: {result.warnings[0][:200]}",
            ))
        if result.contraindications:
            snippets.append(EvidenceSnippet(
                id=_stable_id(drug_ref, "label", "contraindication"),
                kind="openfda_label",
                ref=f"openfda:label:{drug_ref}:contraindication",
                label=f"Contraindication: {result.contraindications[0][:200]}",
            ))
        if result.adverse_reactions_label:
            snippets.append(EvidenceSnippet(
                id=_stable_id(drug_ref, "label", "adverse_reactions"),
                kind="openfda_label",
                ref=f"openfda:label:{drug_ref}:adverse_reactions",
                label=(
                    f"Adverse reactions (from label): "
                    f"{result.adverse_reactions_label[0][:200]}"
                ),
            ))

    return snippets


# ── Internal helpers ───────────────────────────────────────────────────────


def _client() -> httpx.AsyncClient:
    api_key = os.getenv("OPENFDA_API_KEY", "")
    params: dict[str, str] = {}
    if api_key:
        params["api_key"] = api_key
    return httpx.AsyncClient(base_url=BASE_URL, params=params, timeout=15.0)


def _first_text(obj: Any, *path: str) -> str | None:
    """Walk a nested dict/list path and return the first string found.

    OpenFDA often wraps scalar values in single-element lists
    (e.g. ``generic_name: ["LISINOPRIL"]``), so the walker
    auto-unwraps length-1 lists.
    """
    for key in path:
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list):
            if len(obj) == 0:
                return None
            obj = obj[0]
        else:
            return None
    if isinstance(obj, list):
        obj = obj[0] if obj else None
    return str(obj) if obj is not None else None


def _first_text_list(obj: Any, *path: str) -> list[str]:
    """Walk a nested path and return the first list of strings found."""
    for key in path:
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list):
            obj = obj[0] if obj else None
        else:
            return []
    if isinstance(obj, list):
        return [str(item) for item in obj if item]
    text = str(obj) if obj else ""
    return [text] if text else []


def _reaction_reports(results: list[dict]) -> list[str]:
    """Extract reaction PT (preferred term) strings from event results."""
    out: set[str] = set()
    for item in results:
        reactions = item.get("patient", {}).get("reaction", [])
        for r in reactions:
            if isinstance(r, dict):
                pt = r.get("reactionmeddrapt")
                if pt:
                    out.add(str(pt))
    return sorted(out, key=lambda s: -len(s))


_SERIOUSNESS_KEYS = {
    "death": "death",
    "disabling": "disability",
    "hospitalization": "hospitalization",
    "life_threatening": "life_threatening",
    "required_intervention": "required_intervention",
    "other": "other",
}


def _count_by_seriousness(result: dict) -> dict[str, int]:
    """Parse the serious-ness breakdown from an event result."""
    serious = result.get("serious", 0)
    out: dict[str, int] = {}
    if serious:
        out["serious"] = int(serious)
    for field, key in _SERIOUSNESS_KEYS.items():
        val = result.get(field)
        if val:
            out[key] = int(val)
    out["total"] = int(result.get("total", 0) or 0)
    return out


async def _get_json(endpoint: str, search: str, limit: int) -> dict[str, Any]:
    """Rate-limited, cached HTTP GET → parsed JSON."""
    ckey = _cache_key(endpoint, search, limit)

    # Check cache first
    cached = _cache_get(ckey)
    if cached is not None:
        return cached

    await _bucket.acquire()

    async with _client() as client:
        resp = await client.get(
            f"/{endpoint}.json",
            params={"search": search, "limit": limit},
        )

        # Handle rate-limit response
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "60"))
            await asyncio.sleep(retry_after)
            resp = await client.get(
                f"/{endpoint}.json",
                params={"search": search, "limit": limit},
            )

        resp.raise_for_status()
        body = resp.json()

    _cache_set(ckey, body)
    return body


# ── Public API ─────────────────────────────────────────────────────────────


async def lookup_adverse_events(
    *,
    rxcui: str | None = None,
    generic_name: str | None = None,
    limit: int = 10,
) -> list[OpenFdaResult]:
    """Query the FDA adverse-event endpoint (``/event``) for one or more
    drugs identified by RxCUI or generic name.

    Parameters
    ----------
    rxcui : str | None
        RxNorm RxCUI identifier.
    generic_name : str | None
        Generic drug name (e.g. ``\"lisinopril\"``).
    limit : int
        Maximum number of results (default 10).

    Returns
    -------
    list[OpenFdaResult]
        One entry per result returned by the API.
    """
    if rxcui:
        search = f"patient.drug.openfda.rxcui:{rxcui}"
    elif generic_name:
        search = f'patient.drug.openfda.generic_name:"{generic_name}"'
    else:
        raise ValueError("Provide either rxcui or generic_name")

    body = await _get_json("event", search, limit)
    results_raw = body.get("results", [])

    # Collapse metadata once
    meta = body.get("meta", {}).get("results", {})
    total_events = int(meta.get("total", 0))
    event_counts = _count_by_seriousness(meta)
    reactions = _reaction_reports(results_raw)

    results: list[OpenFdaResult] = []
    for item in results_raw:
        drugs = item.get("patient", {}).get("drug", [])
        candidate: dict | None = None
        for d in drugs:
            of = d.get("openfda", {})
            rxcuis = of.get("rxcui", [])
            gnames = of.get("generic_name", [])
            if rxcui and rxcui in rxcuis:
                candidate = d
                break
            if generic_name and generic_name.lower() in {g.lower() for g in gnames}:
                candidate = d
                break
        if candidate is None and drugs:
            candidate = drugs[0]

        r = OpenFdaResult(
            rxcui=rxcui or _first_text(candidate, "openfda", "rxcui"),
            generic_name=generic_name
            or _first_text(candidate, "openfda", "generic_name"),
            brand_name=_first_text(candidate, "openfda", "brand_name"),
            manufacturer=_first_text(item, "companynumb"),
            serious_reactions=reactions,
            total_events=total_events,
            event_count_by_seriousness=event_counts,
            raw_event=item,
        )
        r.evidence_snippets = _build_snippets(r, source="adverse_events")
        results.append(r)

    return results


async def lookup_label(
    *,
    rxcui: str | None = None,
    generic_name: str | None = None,
    limit: int = 1,
) -> list[OpenFdaResult]:
    """Query the FDA drug-label endpoint (``/label``) for one or more
    drugs identified by RxCUI or generic name.

    Parameters
    ----------
    rxcui : str | None
        RxNorm RxCUI identifier.
    generic_name : str | None
        Generic drug name (e.g. ``\"lisinopril\"``).
    limit : int
        Maximum number of results (default 1).

    Returns
    -------
    list[OpenFdaResult]
        One entry per result returned by the API.
    """
    if rxcui:
        search = f"openfda.rxcui:{rxcui}"
    elif generic_name:
        search = f'openfda.generic_name:"{generic_name}"'
    else:
        raise ValueError("Provide either rxcui or generic_name")

    body = await _get_json("label", search, limit)
    results_raw = body.get("results", [])

    results: list[OpenFdaResult] = []
    for item in results_raw:
        r = OpenFdaResult(
            rxcui=rxcui or _first_text(item, "openfda", "rxcui"),
            generic_name=generic_name or _first_text(item, "openfda", "generic_name"),
            brand_name=_first_text(item, "openfda", "brand_name"),
            manufacturer=_first_text(item, "openfda", "manufacturer_name"),
            indications=_first_text_list(item, "indications_and_usage"),
            warnings=_first_text_list(item, "warnings_and_cautions"),
            contraindications=_first_text_list(item, "contraindications"),
            adverse_reactions_label=_first_text_list(item, "adverse_reactions"),
            boxed_warnings=_first_text_list(item, "boxed_warning"),
            raw_label=item,
        )
        r.evidence_snippets = _build_snippets(r, source="label")
        results.append(r)

    return results


async def lookup_drug(
    *,
    rxcui: str | None = None,
    generic_name: str | None = None,
    event_limit: int = 5,
    label_limit: int = 1,
) -> OpenFdaResult | None:
    """Convenience: combine adverse-event + label lookups for a single drug.

    Parameters
    ----------
    rxcui : str | None
        RxNorm RxCUI identifier.
    generic_name : str | None
        Generic drug name (e.g. ``\"lisinopril\"``).
    event_limit : int
        Max adverse-event results (default 5).
    label_limit : int
        Max label results (default 1 — usually one label is enough).

    Returns
    -------
    OpenFdaResult | None
        A merged result, or ``None`` when nothing is found.
    """
    if not rxcui and not generic_name:
        raise ValueError("Provide either rxcui or generic_name")

    events, labels = None, None
    try:
        events = await lookup_adverse_events(
            rxcui=rxcui, generic_name=generic_name, limit=event_limit
        )
    except httpx.HTTPStatusError:
        pass

    try:
        labels = await lookup_label(
            rxcui=rxcui, generic_name=generic_name, limit=label_limit
        )
    except httpx.HTTPStatusError:
        pass

    if not events and not labels:
        return None

    base = OpenFdaResult()

    if events:
        base = events[0]
        if labels:
            base.indications = labels[0].indications
            base.warnings = labels[0].warnings
            base.contraindications = labels[0].contraindications
            base.adverse_reactions_label = labels[0].adverse_reactions_label
            base.boxed_warnings = labels[0].boxed_warnings
            base.raw_label = labels[0].raw_label
            base.evidence_snippets = (
                base.evidence_snippets + labels[0].evidence_snippets
            )
            if not base.generic_name:
                base.generic_name = labels[0].generic_name
            if not base.brand_name:
                base.brand_name = labels[0].brand_name
            if not base.manufacturer:
                base.manufacturer = labels[0].manufacturer
    elif labels:
        base = labels[0]

    return base
