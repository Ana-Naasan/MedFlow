from __future__ import annotations

import abc
import enum
from dataclasses import dataclass, field
from datetime import datetime


class Capability(enum.Flag):
    PATIENT = enum.auto()
    MEDICATIONS = enum.auto()
    CONDITIONS = enum.auto()
    ALLERGIES = enum.auto()
    OBSERVATIONS = enum.auto()
    PROCEDURES = enum.auto()


@dataclass(slots=True)
class Provenance:
    resource_ref: str
    source_provider: str
    source_record_id: str | None = None
    span: dict | None = None


@dataclass(slots=True)
class FetchResult:
    bundle: object
    source: str
    fetched_at: datetime
    source_version: str | None = None
    partial: bool = False
    warnings: list[str] = field(default_factory=list)
    provenance: list[Provenance] = field(default_factory=list)
    coverage: dict[str, dict[str, bool]] = field(default_factory=dict)


@dataclass(slots=True)
class HealthStatus:
    ok: bool
    latency_ms: float
    detail: str | None = None


class ConnectorError(Exception):
    """Base class for connector failures."""


class ConnectorUnavailable(ConnectorError):
    """Raised when a source is unreachable."""


class ConnectorDataError(ConnectorError):
    """Raised when source data cannot be normalized."""


class Provider(abc.ABC):
    id: str
    capabilities: Capability

    @abc.abstractmethod
    async def fetch_patient(self, patient_id: str) -> FetchResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def health_check(self) -> HealthStatus:
        raise NotImplementedError

    def supports(self, cap: Capability) -> bool:
        return cap in self.capabilities
