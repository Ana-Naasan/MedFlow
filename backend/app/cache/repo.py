from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.cache.models import AuditEvent, CachedResource, EvidenceCard


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def upsert_resource(
    session: AsyncSession,
    *,
    patient_id: str,
    resource_type: str,
    resource_id: str,
    body: dict,
    source_provider: str,
) -> CachedResource:
    """Insert or update a cached FHIR resource; never creates duplicates."""
    row = await session.get(CachedResource, (patient_id, resource_type, resource_id))
    if row is None:
        row = CachedResource(
            patient_id=patient_id,
            resource_type=resource_type,
            resource_id=resource_id,
            body=body,
            source_provider=source_provider,
        )
        session.add(row)
    else:
        row.body = body
        row.source_provider = source_provider
        row.updated_at = _now()
    await session.flush()
    return row


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
