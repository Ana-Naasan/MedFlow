from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB

from backend.app.database import Base

# JSONB on Postgres; plain JSON on every other dialect (SQLite for tests).
_JSONB = JSON().with_variant(_PG_JSONB(), "postgresql")


def _now() -> datetime:
    return datetime.now(UTC)


class CachedResource(Base):
    """One row per FHIR resource fetched from a connector."""

    __tablename__ = "cached_resource"

    patient_id = Column(String, primary_key=True)
    resource_type = Column(String, primary_key=True)
    resource_id = Column(String, primary_key=True)
    body = Column(_JSONB, nullable=False)
    source_provider = Column(String, nullable=False)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    # TTL for refresh-on-read (CACHE-02). NULL = never expires.
    expires_at = Column(DateTime(timezone=True), nullable=True)


class EvidenceCard(Base):
    """Drug-knowledge snippet stored by a stable, human-readable id."""

    __tablename__ = "evidence_card"

    id = Column(String, primary_key=True)
    kind = Column(String, nullable=False)  # e.g. "ddinter", "acb", "beers", "openfda"
    body = Column(_JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class AuditEvent(Base):
    """Immutable record written on every cache read."""

    __tablename__ = "audit_event"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False)  # "resource_read" | "evidence_read"
    patient_id = Column(String, nullable=True)
    resource_ref = Column(String, nullable=False)  # e.g. "Condition/cond-001"
    actor = Column(String, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class HypothesisRecord(Base):
    """Persisted hypothesis state for confirm/dismiss actions."""

    __tablename__ = "hypothesis"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    group = Column(String, nullable=True)  # stable cross-ref key for dismiss-similar
    status = Column(String, nullable=False, default="pending")  # pending|confirmed|dismissed
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now)
