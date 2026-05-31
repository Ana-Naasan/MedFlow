"""MockFHIR connector — fetches patient data from the public HAPI FHIR R4 test server.

Demo mode (snapshot-first): if seeds/mock_fhir_snapshot.json exists the provider
returns it directly with no network access.  On first live fetch the trimmed,
validated bundle is written there automatically.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from backend.app.providers.base import (
    Capability,
    ConnectorDataError,
    ConnectorUnavailable,
    FetchResult,
    HealthStatus,
    Provider,
    Provenance,
)

_BASE_URL = "https://hapi.fhir.org/baseR4"
_SEEDS_DIR = Path(__file__).parent.parent / "seeds"
_DEFAULT_SNAPSHOT = _SEEDS_DIR / "mock_fhir_snapshot.json"

_KEPT_TYPES = frozenset({
    "Patient",
    "Condition",
    "MedicationStatement",
    "Observation",
    "AllergyIntolerance",
    "Procedure",
})

_TYPE_TO_CAP = {
    "Patient": "patient",
    "Condition": "conditions",
    "MedicationStatement": "medications",
    "Observation": "observations",
    "AllergyIntolerance": "allergies",
    "Procedure": "procedures",
}


# ── validators (lazy-loaded so the module imports without fhir.resources) ────

_VALIDATORS: dict[str, type] = {}


def _load_validators() -> dict[str, type]:
    global _VALIDATORS
    if _VALIDATORS:
        return _VALIDATORS
    from fhir.resources.R4B.allergyintolerance import AllergyIntolerance
    from fhir.resources.R4B.condition import Condition
    from fhir.resources.R4B.medicationstatement import MedicationStatement
    from fhir.resources.R4B.observation import Observation
    from fhir.resources.R4B.patient import Patient
    from fhir.resources.R4B.procedure import Procedure

    _VALIDATORS = {
        "Patient": Patient,
        "Condition": Condition,
        "MedicationStatement": MedicationStatement,
        "Observation": Observation,
        "AllergyIntolerance": AllergyIntolerance,
        "Procedure": Procedure,
    }
    return _VALIDATORS


# ── module-level helpers ─────────────────────────────────────────────────────


def _trim_and_validate(
    entries: list[dict],
    patient_id: str = "",
    *,
    _validators: dict[str, type] | None = None,
) -> tuple[list[dict], list[str]]:
    """Filter entries to our 6 resource types and re-validate each one.

    *_validators* is injectable so tests can run without fhir.resources.
    Returns (validated_resource_dicts, warning_strings).
    """
    validators = _validators if _validators is not None else _load_validators()
    validated: list[dict] = []
    warnings: list[str] = []

    for entry in entries:
        raw = entry.get("resource", entry)
        if not isinstance(raw, dict):
            continue
        rtype = raw.get("resourceType")
        if rtype not in validators:
            continue
        try:
            model = validators[rtype].model_validate(raw)
            validated.append(model.model_dump(exclude_none=True))
        except Exception as exc:
            rid = raw.get("id", "?")
            warnings.append(f"Skipped {rtype}/{rid}: {exc}")

    return validated, warnings


def _save_snapshot(path: Path, bundle: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, indent=2, default=str))


def _make_result(
    bundle: dict,
    patient_id: str,
    source: str,
    warnings: list[str],
) -> FetchResult:
    entries = bundle.get("entry", [])
    provenance: list[Provenance] = []
    coverage: dict[str, dict[str, bool]] = {}
    seen: set[str] = set()

    for entry in entries:
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType", "")
        rid = resource.get("id", "")
        cap_key = _TYPE_TO_CAP.get(rtype)
        if cap_key and cap_key not in seen:
            coverage[cap_key] = {"requested": True, "returned": True}
            seen.add(cap_key)
        if rtype and rid:
            provenance.append(
                Provenance(
                    resource_ref=f"{rtype}/{rid}",
                    source_provider=source,
                    source_record_id=rid,
                )
            )

    for cap_key in _TYPE_TO_CAP.values():
        if cap_key not in coverage:
            coverage[cap_key] = {"requested": True, "returned": False}

    return FetchResult(
        bundle=bundle,
        source=source,
        fetched_at=datetime.now(UTC),
        partial=bool(warnings),
        warnings=warnings,
        provenance=provenance,
        coverage=coverage,
    )


async def _fetch_raw_entries(client, patient_id: str) -> list[dict]:
    """Fetch all 6 resource types from the HAPI server and return raw entry dicts."""
    entries: list[dict] = []

    try:
        patient = await client.resources("Patient").search(_id=patient_id).first()
        if patient:
            entries.append({"resource": patient.serialize()})
    except Exception:
        pass

    for rtype, params in [
        ("Condition", {"subject": patient_id}),
        ("MedicationStatement", {"subject": patient_id}),
        ("Observation", {"subject": patient_id}),
        ("Procedure", {"subject": patient_id}),
    ]:
        try:
            results = await client.resources(rtype).search(**params).fetch()
            for r in results:
                entries.append({"resource": r.serialize()})
        except Exception:
            pass

    try:
        allergies = await client.resources("AllergyIntolerance").search(patient=patient_id).fetch()
        for r in allergies:
            entries.append({"resource": r.serialize()})
    except Exception:
        pass

    return entries


# ── Provider ─────────────────────────────────────────────────────────────────


class MockFHIRProvider(Provider):
    """Fetches patient data from the public HAPI FHIR R4 test server.

    Snapshot-first: if ``snapshot_path`` exists the file is returned with no
    network access (demo mode).  On the first live fetch the trimmed, validated
    bundle is saved there automatically.
    """

    id = "mock-fhir"
    capabilities = (
        Capability.PATIENT
        | Capability.MEDICATIONS
        | Capability.CONDITIONS
        | Capability.ALLERGIES
        | Capability.OBSERVATIONS
        | Capability.PROCEDURES
    )

    def __init__(
        self,
        *,
        base_url: str = _BASE_URL,
        snapshot_path: Path | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._snapshot_path = snapshot_path if snapshot_path is not None else _DEFAULT_SNAPSHOT

    async def fetch_patient(self, patient_id: str) -> FetchResult:
        if self._snapshot_path.exists():
            return self._load_snapshot(patient_id)
        return await self._fetch_live(patient_id)

    async def health_check(self) -> HealthStatus:
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/metadata")
            latency_ms = (time.monotonic() - t0) * 1000
            ok = resp.status_code < 400
            return HealthStatus(
                ok=ok,
                latency_ms=latency_ms,
                detail=None if ok else f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            return HealthStatus(ok=False, latency_ms=0.0, detail=str(exc))

    # ── internals ────────────────────────────────────────────────────────────

    async def _fetch_live(self, patient_id: str) -> FetchResult:
        try:
            from fhirpy import AsyncFHIRClient
        except ImportError as exc:
            raise ConnectorDataError("fhirpy is not installed; add it to requirements.txt") from exc

        try:
            client = AsyncFHIRClient(self._base_url)
            raw_entries = await _fetch_raw_entries(client, patient_id)
        except Exception as exc:
            raise ConnectorUnavailable(f"HAPI FHIR server unreachable: {exc}") from exc

        validated, warnings = _trim_and_validate(raw_entries, patient_id)
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": [{"resource": r} for r in validated],
        }
        _save_snapshot(self._snapshot_path, bundle)
        return _make_result(bundle, patient_id, self.id, warnings)

    def _load_snapshot(self, patient_id: str) -> FetchResult:
        try:
            bundle = json.loads(self._snapshot_path.read_text())
        except Exception as exc:
            raise ConnectorDataError(
                f"Cannot read snapshot at {self._snapshot_path}: {exc}"
            ) from exc
        return _make_result(bundle, patient_id, self.id, warnings=["loaded from local snapshot"])
