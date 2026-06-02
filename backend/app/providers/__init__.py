"""Provider abstractions for Umraa."""

from pathlib import Path

from backend.app.config import INSTITUTION_A_DSN, INSTITUTION_B_DSN
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
from backend.app.providers.pdf import PDFProvider, TextSpan
from backend.app.providers.postgres import PostgresProvider
from backend.app.providers.registry import ConnectorNotFound, build, list_connectors, register
from backend.app.seeds.sample_hl7 import SAMPLE_ADT_A01

# Default-to-seeded sources: a connector is configured for a source at registration
# (the plugin model — point it at a hospital's feed once), and Umraa's own seeded
# sources make the project work standalone. The optional kwargs let a caller/test
# override the source without changing the /intake contract.
_SEEDED_PDF = Path(__file__).parent.parent / "seeds" / "sample_clinical.pdf"

register("mock-fhir", MockFHIRProvider)
register("pdf", lambda **kwargs: PDFProvider(kwargs.get("path") or _SEEDED_PDF))
register("hl7v2", lambda **kwargs: HL7v2Provider(kwargs.get("raw_message") or SAMPLE_ADT_A01))
# The flagship integration story: one PostgresProvider reads two deliberately
# different institution schemas. Registered as two named connectors so the
# generality is visible at /intake; both default to their seeded institution DB.
register(
    "institution-a",
    lambda **kwargs: PostgresProvider(
        dsn=kwargs.get("dsn") or INSTITUTION_A_DSN, institution="a", pool=kwargs.get("pool")
    ),
)
register(
    "institution-b",
    lambda **kwargs: PostgresProvider(
        dsn=kwargs.get("dsn") or INSTITUTION_B_DSN, institution="b", pool=kwargs.get("pool")
    ),
)

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
    "PDFProvider",
    "PostgresProvider",
    "Provider",
    "Provenance",
    "TextSpan",
    "build",
    "list_connectors",
    "register",
]
