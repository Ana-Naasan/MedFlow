from __future__ import annotations

import enum
import hashlib
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import distinct, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.cache.models import AuditEvent, CachedResource, EvidenceCard, HypothesisRecord


def _now() -> datetime:
    return datetime.now(UTC)


class CacheStatus(str, enum.Enum):
    """Outcome of a refresh-on-read, mapped by the API to the ``X-Cache`` header."""

    HIT = "HIT"  # served fresh (or stale-on-lost-race) from cache, no re-pull
    REFRESH = "REFRESH"  # this caller won the lock and re-pulled from the source
    MISS = "MISS"  # nothing cached and nothing fetched


async def upsert_resource(
    session: AsyncSession,
    *,
    patient_id: str,
    resource_type: str,
    resource_id: str,
    body: dict,
    source_provider: str,
    ttl_seconds: int | None = None,
) -> CachedResource:
    """Insert or update a cached FHIR resource; never creates duplicates.

    When *ttl_seconds* is given the row's ``expires_at`` is set to now+ttl so
    refresh-on-read (CACHE-02) can detect staleness; ``None`` leaves it
    unset (never expires).
    """
    expires_at = _now() + timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None
    row = await session.get(CachedResource, (patient_id, resource_type, resource_id))
    if row is None:
        row = CachedResource(
            patient_id=patient_id,
            resource_type=resource_type,
            resource_id=resource_id,
            body=body,
            source_provider=source_provider,
            expires_at=expires_at,
        )
        session.add(row)
    else:
        row.body = body
        row.source_provider = source_provider
        row.updated_at = _now()
        if ttl_seconds is not None:
            row.expires_at = expires_at
    await session.flush()
    return row


async def delete_resource(
    session: AsyncSession,
    *,
    patient_id: str,
    resource_type: str,
    resource_id: str,
) -> bool:
    """Delete a cached resource by its composite key; flush immediately.

    Returns ``True`` if a row was removed. Used to clear a stale partial-data
    notice once a source recovers (#91) — without this the FetchMetadata row is
    only ever upserted, so a recovered patient keeps showing old gaps forever.
    """
    row = await session.get(CachedResource, (patient_id, resource_type, resource_id))
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


def _is_expired(row: CachedResource, *, now: datetime | None = None) -> bool:
    """A row with no ``expires_at`` never expires; otherwise compare to now.

    SQLite returns tz-naive datetimes (Postgres preserves tz), so coerce a
    naive ``expires_at`` to UTC before comparing to avoid a naive/aware clash.
    """
    if row.expires_at is None:
        return False
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= (now or _now())


def _advisory_key(patient_id: str, resource_type: str, resource_id: str) -> int:
    """Deterministic signed 64-bit key for ``pg_try_advisory_xact_lock(bigint)``."""
    digest = hashlib.blake2b(
        f"{patient_id}/{resource_type}/{resource_id}".encode(), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big", signed=True)


async def _try_advisory_xact_lock(session: AsyncSession, key: int) -> bool:
    """Try to take a transaction-scoped advisory lock.

    Postgres-native via ``pg_try_advisory_xact_lock``: the winner re-pulls while
    other transactions serve cache. On non-Postgres dialects (SQLite in tests)
    there is no shared lock, so we grant it optimistically — refresh is then
    single-writer, which is correct for the test/dev path.
    """
    if session.bind is None or session.bind.dialect.name != "postgresql":
        return True
    result = await session.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": key})
    return bool(result.scalar())


async def get_or_refresh(
    session: AsyncSession,
    *,
    patient_id: str,
    resource_type: str,
    resource_id: str,
    actor: str,
    fetcher: Callable[[], Awaitable[dict | None]],
    source_provider: str,
    ttl_seconds: int,
) -> tuple[CachedResource | None, CacheStatus]:
    """Refresh-on-read (CACHE-02/03): serve fresh cache, else re-pull under an
    advisory lock so concurrent readers don't stampede the source.

    Always writes an audit event (CACHE-03). Returns the row (possibly stale or
    ``None``) and a :class:`CacheStatus` for the caller to surface as ``X-Cache``.
    """
    row = await session.get(CachedResource, (patient_id, resource_type, resource_id))

    if row is not None and not _is_expired(row):
        status = CacheStatus.HIT
    elif await _try_advisory_xact_lock(
        session, _advisory_key(patient_id, resource_type, resource_id)
    ):
        body = await fetcher()
        if body is not None:
            row = await upsert_resource(
                session,
                patient_id=patient_id,
                resource_type=resource_type,
                resource_id=resource_id,
                body=body,
                source_provider=source_provider,
                ttl_seconds=ttl_seconds,
            )
            status = CacheStatus.REFRESH
        else:
            # Source returned nothing — serve whatever we already had.
            status = CacheStatus.HIT if row is not None else CacheStatus.MISS
    else:
        # Lost the race — another caller is refreshing; serve current cache.
        status = CacheStatus.HIT if row is not None else CacheStatus.MISS

    await write_audit_event(
        session,
        event_type="resource_read",
        resource_ref=f"{resource_type}/{resource_id}",
        actor=actor,
        patient_id=patient_id,
    )
    return row, status


async def get_resource(
    session: AsyncSession,
    *,
    patient_id: str,
    resource_type: str,
    resource_id: str,
    actor: str,
) -> CachedResource | None:
    """Fetch a cached resource and write an audit event unconditionally."""
    row = await session.get(CachedResource, (patient_id, resource_type, resource_id))
    await write_audit_event(
        session,
        event_type="resource_read",
        resource_ref=f"{resource_type}/{resource_id}",
        actor=actor,
        patient_id=patient_id,
    )
    return row


async def upsert_evidence_card(
    session: AsyncSession,
    *,
    evidence_id: str,
    kind: str,
    body: dict,
) -> EvidenceCard:
    """Insert or update an evidence snippet by its stable id."""
    row = await session.get(EvidenceCard, evidence_id)
    if row is None:
        row = EvidenceCard(id=evidence_id, kind=kind, body=body)
        session.add(row)
    else:
        row.kind = kind
        row.body = body
        row.updated_at = _now()
    await session.flush()
    return row


async def get_evidence_card(
    session: AsyncSession,
    *,
    evidence_id: str,
    actor: str,
) -> EvidenceCard | None:
    """Fetch an evidence card and write an audit event unconditionally."""
    row = await session.get(EvidenceCard, evidence_id)
    await write_audit_event(
        session,
        event_type="evidence_read",
        resource_ref=f"evidence/{evidence_id}",
        actor=actor,
    )
    return row


async def write_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    resource_ref: str,
    actor: str,
    patient_id: str | None = None,
) -> AuditEvent:
    """Append an immutable audit record; always flushes immediately."""
    event = AuditEvent(
        id=str(uuid.uuid4()),
        event_type=event_type,
        patient_id=patient_id,
        resource_ref=resource_ref,
        actor=actor,
    )
    session.add(event)
    await session.flush()
    return event


async def list_patient_ids_from_db(session: AsyncSession) -> list[str]:
    """Return distinct patient_ids that have at least one cached resource."""
    result = await session.execute(select(distinct(CachedResource.patient_id)))
    return [row for (row,) in result]


# Cache rows that are bookkeeping, not citable FHIR resources — excluded from the
# patient resource read path so reasoning + citations only ever see real FHIR data.
_NON_FHIR_RESOURCE_TYPES = ("FetchMetadata", "DecisionPacket")


async def list_patient_resources(session: AsyncSession, *, patient_id: str) -> list[CachedResource]:
    """Return a patient's cached FHIR resource rows (excluding bookkeeping rows).

    Feeds the packet build + citation read path for intake'd patients, whose fetched
    resources live in ``cached_resource`` rather than the static seed store. The
    synthetic ``FetchMetadata`` partial-data notice and the cached ``DecisionPacket``
    are excluded so they are never reasoned over or cited. No audit event — this is
    an internal bulk read feeding the packet build, not a per-citation access (those
    go through :func:`get_resource`, which audits).
    """
    result = await session.execute(
        select(CachedResource).where(
            CachedResource.patient_id == patient_id,
            CachedResource.resource_type.not_in(_NON_FHIR_RESOURCE_TYPES),
        )
    )
    return list(result.scalars().all())


async def list_audit_events(session: AsyncSession, limit: int = 50) -> list[AuditEvent]:
    """Return the most recent audit events, newest first (API-05).

    Ordered by ``occurred_at`` DESC and capped at *limit* rows so the read
    endpoint can't accidentally stream the whole immutable audit log.
    """
    result = await session.execute(
        select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def upsert_hypothesis(
    session: AsyncSession,
    *,
    id: str,
    patient_id: str,
    title: str,
    group: str | None = None,
) -> HypothesisRecord:
    """Insert or update a hypothesis record without changing its status."""
    row = await session.get(HypothesisRecord, id)
    if row is None:
        row = HypothesisRecord(
            id=id,
            patient_id=patient_id,
            title=title,
            group=group,
        )
        session.add(row)
    else:
        row.title = title
        row.group = group
        row.updated_at = _now()
    await session.flush()
    return row


async def _resolve_hypothesis(
    session: AsyncSession, *, id: str, patient_id: str
) -> HypothesisRecord | None:
    """Resolve a hypothesis row by raw id, falling back to the patient-namespaced
    storage key (``{patient_id}:{id}``).

    Packets are served with un-prefixed hypothesis ids (``hyp-001``) while rows
    are persisted under ``{patient_id}:{id}`` to stay collision-free across
    patients. This lets confirm/dismiss accept the id the UI actually sends.
    """
    row = await session.get(HypothesisRecord, id)
    if row is None and patient_id and not id.startswith(f"{patient_id}:"):
        row = await session.get(HypothesisRecord, f"{patient_id}:{id}")
    return row


async def confirm_hypothesis(
    session: AsyncSession,
    *,
    id: str,
    actor: str,
    patient_id: str,
) -> HypothesisRecord | None:
    """Mark a hypothesis confirmed and write an audit event. Returns None if not found."""
    row = await _resolve_hypothesis(session, id=id, patient_id=patient_id)
    if row is None:
        return None
    if row.status == "confirmed":
        # Idempotent: already confirmed — no state change, no duplicate audit row.
        return row
    row.status = "confirmed"
    row.updated_at = _now()
    await session.flush()
    await write_audit_event(
        session,
        event_type="hypothesis_confirmed",
        resource_ref=f"hypothesis/{id}",
        actor=actor,
        patient_id=patient_id,
    )
    return row


async def dismiss_hypothesis(
    session: AsyncSession,
    *,
    id: str,
    actor: str,
    patient_id: str,
) -> list[str]:
    """Dismiss a hypothesis and all similar ones (by group, then by title).

    Returns the list of dismissed IDs. Returns an empty list if the target
    hypothesis is not found.
    """
    target = await _resolve_hypothesis(session, id=id, patient_id=patient_id)
    if target is None:
        return []

    # Build the query for siblings: same group (if set) or exact title match.
    if target.group is not None:
        result = await session.execute(
            select(HypothesisRecord).where(
                HypothesisRecord.patient_id == patient_id,
                HypothesisRecord.group == target.group,
            )
        )
    else:
        result = await session.execute(
            select(HypothesisRecord).where(
                HypothesisRecord.patient_id == patient_id,
                HypothesisRecord.title == target.title,
            )
        )

    rows = result.scalars().all()
    dismissed_ids: list[str] = []
    changed = 0
    for row in rows:
        if row.status != "dismissed":
            row.status = "dismissed"
            row.updated_at = _now()
            changed += 1
        dismissed_ids.append(row.id)

    # Idempotent: only audit when something actually transitioned to dismissed.
    # Re-dismissing an already-dismissed hypothesis is a no-op (no duplicate audit)
    # but still returns the dismissed set so the endpoint stays 200, not 404.
    if changed:
        await session.flush()
        await write_audit_event(
            session,
            event_type="hypothesis_dismissed",
            resource_ref=f"hypothesis/{id}",
            actor=actor,
            patient_id=patient_id,
        )
    return dismissed_ids
