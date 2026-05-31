"""OpenFDA adverse-event and drug-label lookups with rate limiting, caching,
and evidence-snippet extraction.

Real-API contract (verified against open.fda.gov, 2026-05-31)
-------------------------------------------------------------
* A normal ``/drug/event.json?search=...`` query returns
  ``meta.results = {skip, limit, total}`` — it does **not** carry per-seriousness
  counts. To count events by seriousness we run one filtered query per flag
  (``search=<drug>+AND+seriousnessdeath:1&limit=1``) and read ``meta.results.total``.
* Most-frequent reactions come from an aggregation query
  (``count=patient.reaction.reactionmeddrapt.exact``) whose buckets are the
  **top-level** ``results`` array of ``{term, count}`` (a count query has no
  ``meta.results``).
* Every ``openfda`` sub-field (rxcui, generic_name, ...) is an *array of strings*
  and the ``openfda`` block may be absent. Label section fields
  (boxed_warning, warnings, ...) are arrays of strings and are sparse.

Rate limits
-----------
OpenFDA allows ~240 requests/min with an API key (``OPENFDA_API_KEY``). We keep
an in-memory token bucket below that. Responses are cached process-locally with
a 1-hour TTL and a bounded size.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import md5
from typing import Any

import httpx

from backend.app.dtos import EvidenceSnippet  # re-exported for backward-compat imports

BASE_URL = "https://api.fda.gov/drug"

_RATE_LIMIT_RATE = 200  # tokens per minute (below the 240 cap)
_RATE_LIMIT_BURST = 20
_CACHE_TTL = 3600  # seconds
_CACHE_MAX_SIZE = 512  # bounded LRU-ish eviction

# Reaction aggregation field (.exact counts whole phrases, not tokenised words).
_REACTION_COUNT_FIELD = "patient.reaction.reactionmeddrapt.exact"

# Seriousness flags we surface, mapped {our_key: openFDA_field}. Filtered as
# "<field>:1" against /event; the count is meta.results.total of that query.
_SERIOUSNESS_FLAGS: dict[str, str] = {
    "death": "seriousnessdeath",
    "hospitalization": "seriousnesshospitalization",
    "serious": "serious",
}

# ── Data containers ────────────────────────────────────────────────────────


@dataclass
class OpenFdaResult:
    """Normalised, drug-level OpenFDA data."""

    rxcui: str | None = None
    generic_name: str | None = None
    brand_name: str | None = None
    manufacturer: str | None = None

    # Adverse reactions (from /event)
    total_events: int = 0
    reaction_counts: list[tuple[str, int]] = field(default_factory=list)  # real (term, count)
    event_count_by_seriousness: dict[str, int] = field(default_factory=dict)

    # Label snippets (from /label)
    indications: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    contraindications: list[str] = field(default_factory=list)
    adverse_reactions_label: list[str] = field(default_factory=list)
    boxed_warnings: list[str] = field(default_factory=list)

    evidence_snippets: list[EvidenceSnippet] = field(default_factory=list)

    raw_event: dict[str, Any] | None = None
    raw_label: dict[str, Any] | None = None

    @property
    def serious_reactions(self) -> list[str]:
        """Reaction terms ordered by real report frequency (desc)."""
        return [term for term, _ in self.reaction_counts]


# ── Token-bucket rate limiter ──────────────────────────────────────────────


class _TokenBucket:
    """Simple in-process token-bucket rate limiter."""

    def __init__(self, rate: float, burst: int) -> None:
        self._rate = rate / 60.0  # tokens per second
        self._burst = burst
        self._tokens = float(burst)
        self._last = time.monotonic()

    async def acquire(self) -> None:
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
    data: dict[str, Any]
    fetched_at: float


_cache: OrderedDict[str, _CacheEntry] = OrderedDict()


def _cache_key(endpoint: str, params: Mapping[str, Any]) -> str:
    """Stable key for (endpoint, query params). Param order does not matter."""
    raw = endpoint + "|" + json.dumps(dict(params), sort_keys=True)
    return md5(raw.encode()).hexdigest()


def _cache_get(key: str) -> dict[str, Any] | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    if time.monotonic() - entry.fetched_at > _CACHE_TTL:
        del _cache[key]
        return None
    _cache.move_to_end(key)
    return entry.data


def _cache_set(key: str, data: dict[str, Any]) -> None:
    _cache[key] = _CacheEntry(data=data, fetched_at=time.monotonic())
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_MAX_SIZE:
        _cache.popitem(last=False)  # evict oldest


# ── Query building ─────────────────────────────────────────────────────────


def _escape_value(value: str) -> str:
    """Quote+escape a value for an openFDA (Lucene/Elasticsearch) query.

    The value is ALWAYS wrapped in double quotes and embedded backslashes/quotes
    are escaped. Inside a quoted phrase every other Lucene metacharacter
    (``+ - && || ! ( ) { } [ ] ^ ~ * ? :`` and the ``AND``/``OR`` operators) is
    treated literally, so a caller-supplied drug name cannot rewrite the query's
    boolean structure (Lucene injection). Quoting unconditionally — rather than
    only when whitespace is present — is what closes the no-space injection hole.
    """
    cleaned = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{cleaned}"'


def _drug_filter(field_prefix: str, rxcui: str | None, generic_name: str | None) -> str:
    """Build the drug search filter for a given field prefix.

    *field_prefix* is ``patient.drug.openfda`` for /event or ``openfda`` for /label.
    """
    if rxcui:
        return f"{field_prefix}.rxcui:{_escape_value(rxcui)}"
    if generic_name:
        return f"{field_prefix}.generic_name:{_escape_value(generic_name)}"
    raise ValueError("Provide either rxcui or generic_name")


# ── Internal HTTP helpers ──────────────────────────────────────────────────


def _client() -> httpx.AsyncClient:
    api_key = os.getenv("OPENFDA_API_KEY", "")
    params: dict[str, str] = {}
    if api_key:
        params["api_key"] = api_key
    return httpx.AsyncClient(base_url=BASE_URL, params=params, timeout=15.0)


async def _get_json(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    """Rate-limited, cached HTTP GET → parsed JSON. Cache keyed by full params."""
    ckey = _cache_key(endpoint, params)
    cached = _cache_get(ckey)
    if cached is not None:
        return cached

    await _bucket.acquire()
    async with _client() as client:
        resp = await client.get(f"/{endpoint}.json", params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "60"))
            await asyncio.sleep(retry_after)
            resp = await client.get(f"/{endpoint}.json", params=params)
        resp.raise_for_status()
        body = resp.json()

    _cache_set(ckey, body)
    return body


def _meta_total(body: dict[str, Any]) -> int:
    return int(body.get("meta", {}).get("results", {}).get("total", 0) or 0)


# ── Parsing helpers ────────────────────────────────────────────────────────


def _first_text(obj: Any, *path: str) -> str | None:
    """Walk a nested dict/list path, returning the first scalar string.

    OpenFDA wraps scalars in single-element lists (e.g. ``generic_name: ["LISINOPRIL"]``),
    so length-1 lists are auto-unwrapped.
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
    """Walk a nested path and return the first list of strings found (sparse-safe)."""
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


def _drug_metadata(results_raw: list[dict], rxcui: str | None, generic_name: str | None) -> dict:
    """Pull rxcui/generic/brand/manufacturer off the best-matching sample record."""
    for item in results_raw:
        for d in item.get("patient", {}).get("drug", []):
            of = d.get("openfda", {})
            rxcuis = of.get("rxcui", [])
            gnames = [g.lower() for g in of.get("generic_name", [])]
            if rxcui and rxcui in rxcuis:
                return of
            if generic_name and generic_name.lower() in gnames:
                return of
    # fall back to the first drug entry that carries an openfda block
    for item in results_raw:
        for d in item.get("patient", {}).get("drug", []):
            if d.get("openfda"):
                return d["openfda"]
    return {}


# ── Evidence snippets ──────────────────────────────────────────────────────


def _stable_id(drug_ref: str, *parts: str) -> str:
    """Deterministic, stable evidence-snippet ID."""
    safe = drug_ref.replace(" ", "_").lower() if drug_ref else "unknown"
    return "openfda:" + ":".join([safe, *parts])


_SERIOUSNESS_SNIPPET_TEXT = {
    "death": "involved death",
    "hospitalization": "involved hospitalisation",
}


def _build_snippets(result: OpenFdaResult, source: str) -> list[EvidenceSnippet]:
    """Evidence bullet points with stable IDs (source: 'adverse_events' | 'label')."""
    snippets: list[EvidenceSnippet] = []
    drug_ref = result.rxcui or result.generic_name or ""
    drug_label = result.generic_name or result.brand_name or result.rxcui or "this drug"

    if source == "adverse_events":
        if result.total_events:
            snippets.append(
                EvidenceSnippet(
                    id=_stable_id(drug_ref, "adverse_events", "total_count"),
                    kind="openfda_adverse_event",
                    ref=f"openfda:adverse_events:{drug_ref}:total_count",
                    label=f"{result.total_events:,} adverse events reported for {drug_label}.",
                )
            )
        if result.reaction_counts:
            top = result.reaction_counts[:5]
            rendered = ", ".join(f"{term} ({count:,})" for term, count in top)
            snippets.append(
                EvidenceSnippet(
                    id=_stable_id(drug_ref, "adverse_events", "top_reactions"),
                    kind="openfda_adverse_event",
                    ref=f"openfda:adverse_events:{drug_ref}:top_reactions",
                    label=f"Most-reported reactions (by report count): {rendered}.",
                )
            )
        for key, phrase in _SERIOUSNESS_SNIPPET_TEXT.items():
            count = result.event_count_by_seriousness.get(key)
            if count:
                snippets.append(
                    EvidenceSnippet(
                        id=_stable_id(drug_ref, "adverse_events", f"{key}_count"),
                        kind="openfda_adverse_event",
                        ref=f"openfda:adverse_events:{drug_ref}:{key}_count",
                        label=f"{count:,} reported events {phrase}.",
                    )
                )

    if source == "label":
        label_sections = [
            ("boxed_warning", result.boxed_warnings, "BOXED WARNING"),
            ("warning", result.warnings, "WARNING"),
            ("contraindication", result.contraindications, "Contraindication"),
            ("adverse_reactions", result.adverse_reactions_label, "Adverse reactions (from label)"),
        ]
        for part, values, prefix in label_sections:
            if values:
                snippets.append(
                    EvidenceSnippet(
                        id=_stable_id(drug_ref, "label", part),
                        kind="openfda_label",
                        ref=f"openfda:label:{drug_ref}:{part}",
                        label=f"{prefix}: {values[0][:200]}",
                    )
                )

    return snippets


# ── Public API ─────────────────────────────────────────────────────────────


async def lookup_adverse_events(
    *,
    rxcui: str | None = None,
    generic_name: str | None = None,
    limit: int = 10,
) -> list[OpenFdaResult]:
    """Query the FDA adverse-event endpoint for one drug (by RxCUI or generic name).

    Aggregates: total report count, most-frequent reactions with real counts
    (``count=`` aggregation), and per-seriousness counts (one filtered query per
    flag). Returns a single drug-level result in a list, or ``[]`` if nothing matched.
    """
    base = _drug_filter("patient.drug.openfda", rxcui, generic_name)

    main = await _get_json("event", {"search": base, "limit": limit})
    total_events = _meta_total(main)
    results_raw = main.get("results", [])
    if total_events == 0 and not results_raw:
        return []

    # Real most-frequent reactions (with counts).
    counts_body = await _get_json(
        "event", {"search": base, "count": _REACTION_COUNT_FIELD, "limit": 10}
    )
    reaction_counts = [
        (str(b["term"]), int(b["count"]))
        for b in counts_body.get("results", [])
        if b.get("term") is not None and b.get("count") is not None
    ]

    # Real per-seriousness counts (one query each → meta.results.total).
    # The AND operator MUST be space-delimited: httpx encodes the spaces to '+',
    # producing openFDA's real "+AND+" delimiter. A literal "+AND+" in the value
    # would be percent-encoded to "%2BAND%2B" and parsed as one broken term.
    seriousness: dict[str, int] = {}
    for key, flag_field in _SERIOUSNESS_FLAGS.items():
        body = await _get_json("event", {"search": f"{base} AND {flag_field}:1", "limit": 1})
        count = _meta_total(body)
        if count:
            seriousness[key] = count

    of = _drug_metadata(results_raw, rxcui, generic_name)
    result = OpenFdaResult(
        rxcui=rxcui or _first_text(of, "rxcui"),
        generic_name=generic_name or _first_text(of, "generic_name"),
        brand_name=_first_text(of, "brand_name"),
        manufacturer=_first_text(of, "manufacturer_name"),
        total_events=total_events,
        reaction_counts=reaction_counts,
        event_count_by_seriousness=seriousness,
        raw_event=results_raw[0] if results_raw else None,
    )
    result.evidence_snippets = _build_snippets(result, source="adverse_events")
    return [result]


async def lookup_label(
    *,
    rxcui: str | None = None,
    generic_name: str | None = None,
    limit: int = 1,
) -> list[OpenFdaResult]:
    """Query the FDA drug-label endpoint for one drug (by RxCUI or generic name)."""
    base = _drug_filter("openfda", rxcui, generic_name)
    body = await _get_json("label", {"search": base, "limit": limit})
    results_raw = body.get("results", [])

    results: list[OpenFdaResult] = []
    for item in results_raw:
        r = OpenFdaResult(
            rxcui=rxcui or _first_text(item, "openfda", "rxcui"),
            generic_name=generic_name or _first_text(item, "openfda", "generic_name"),
            brand_name=_first_text(item, "openfda", "brand_name"),
            manufacturer=_first_text(item, "openfda", "manufacturer_name"),
            indications=_first_text_list(item, "indications_and_usage"),
            warnings=_first_text_list(item, "warnings"),
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
    """Combine adverse-event + label lookups for a single drug."""
    if not rxcui and not generic_name:
        raise ValueError("Provide either rxcui or generic_name")

    events: list[OpenFdaResult] = []
    labels: list[OpenFdaResult] = []
    try:
        events = await lookup_adverse_events(
            rxcui=rxcui, generic_name=generic_name, limit=event_limit
        )
    except httpx.HTTPStatusError:
        pass
    try:
        labels = await lookup_label(rxcui=rxcui, generic_name=generic_name, limit=label_limit)
    except httpx.HTTPStatusError:
        pass

    if not events and not labels:
        return None

    if events:
        base = events[0]
        if labels:
            lab = labels[0]
            base.indications = lab.indications
            base.warnings = lab.warnings
            base.contraindications = lab.contraindications
            base.adverse_reactions_label = lab.adverse_reactions_label
            base.boxed_warnings = lab.boxed_warnings
            base.raw_label = lab.raw_label
            base.evidence_snippets = base.evidence_snippets + lab.evidence_snippets
            base.generic_name = base.generic_name or lab.generic_name
            base.brand_name = base.brand_name or lab.brand_name
            base.manufacturer = base.manufacturer or lab.manufacturer
        return base
    return labels[0]
