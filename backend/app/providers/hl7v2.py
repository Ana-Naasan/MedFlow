"""HL7v2 ADT scaffold connector — parses patient demographics only."""

from __future__ import annotations

from datetime import UTC, datetime

from hl7apy.parser import parse_message

from backend.app.providers.base import (
    Capability,
    ConnectorDataError,
    FetchResult,
    HealthStatus,
    Provenance,
    Provider,
)


class HL7v2Provider(Provider):
    """Scaffold: parses one HL7v2 ADT^A01 message. Full HL7v2 support is roadmap."""

    id = "hl7v2"
    capabilities = Capability.PATIENT

    def __init__(self, raw_message: str = "") -> None:
        self._raw = raw_message

    async def fetch_patient(self, patient_id: str) -> FetchResult:
        try:
            patient_dict = _parse_adt(self._raw)
        except ConnectorDataError:
            raise
        except Exception as exc:
            raise ConnectorDataError(f"HL7v2 parse failed: {exc}") from exc

        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": [{"resource": patient_dict}],
        }
        return FetchResult(
            bundle=bundle,
            source=self.id,
            fetched_at=datetime.now(UTC),
            partial=True,
            warnings=[
                "HL7v2 support is a scaffold: only PID demographics parsed. "
                "Full HL7v2-to-FHIR mapping is roadmap."
            ],
            coverage={
                "patient": {"requested": True, "returned": True},
                "medications": {"requested": False, "returned": False},
                "conditions": {"requested": False, "returned": False},
                "allergies": {"requested": False, "returned": False},
            },
            provenance=[
                Provenance(
                    resource_ref=f"Patient/{patient_dict.get('id', patient_id)}",
                    source_provider=self.id,
                    source_record_id=patient_id,
                )
            ],
        )

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            ok=True,
            latency_ms=0.0,
            detail="HL7v2 scaffold — parse-only, no live connection.",
        )


def _parse_adt(raw: str) -> dict:
    """Parse PID segment from HL7v2 ADT into a FHIR R4 Patient dict.

    Raises ConnectorDataError on invalid input.
    Only extracts: id, name, gender, birthDate.
    """
    normalised = raw.replace("\r\n", "\r").replace("\n", "\r").strip()

    try:
        msg = parse_message(normalised, find_groups=False)
    except Exception as exc:
        raise ConnectorDataError(f"Failed to parse HL7v2 message: {exc}") from exc

    try:
        pid_er7 = msg.pid.to_er7()
    except Exception as exc:
        raise ConnectorDataError(f"No PID segment: {exc}") from exc

    fields = pid_er7.split("|")

    def _f(idx: int) -> str:
        return fields[idx].strip() if idx < len(fields) else ""

    patient_id = _f(3).split("^")[0]
    if not patient_id:
        # hl7apy auto-materialises an empty PID segment, so a message with no
        # PID does not raise above. Refuse to fabricate a Patient/unknown.
        raise ConnectorDataError("HL7v2 message has no PID-3 patient identifier")

    name_parts = _f(5).split("^")
    family = name_parts[0] if name_parts else ""
    given = name_parts[1] if len(name_parts) > 1 else ""

    dob_raw = _f(7).split("^")[0]
    dob: str | None = None
    if len(dob_raw) >= 8 and dob_raw[:8].isdigit():
        dob = f"{dob_raw[:4]}-{dob_raw[4:6]}-{dob_raw[6:8]}"

    gender = {"M": "male", "F": "female"}.get(_f(8).upper(), "unknown")

    patient: dict = {"resourceType": "Patient", "id": patient_id, "gender": gender}
    if family or given:
        patient["name"] = [{"family": family, "given": [given] if given else []}]
    if dob:
        patient["birthDate"] = dob

    return patient
