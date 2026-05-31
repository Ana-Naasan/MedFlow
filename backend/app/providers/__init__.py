"""Provider abstractions for Umraa."""

from backend.app.providers.base import (
    Capability,
    ConnectorDataError,
    ConnectorError,
    ConnectorUnavailable,
    FetchResult,
    HealthStatus,
    Provenance,
    Provider,
)
from backend.app.providers.hl7v2 import HL7v2Provider
from backend.app.providers.mock_fhir import MockFHIRProvider
from backend.app.providers.postgres import PostgresProvider
from backend.app.providers.registry import ConnectorNotFound, build, list_connectors, register

register("mock-fhir", MockFHIRProvider)

__all__ = [
    "Capability",
    "ConnectorDataError",
    "ConnectorError",
    "ConnectorNotFound",
    "ConnectorUnavailable",
    "FetchResult",
    "HealthStatus",
    "HL7v2Provider",
    "MockFHIRProvider",
    "PostgresProvider",
    "Provider",
    "Provenance",
    "build",
    "list_connectors",
    "register",
]
