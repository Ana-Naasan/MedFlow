"""Smoke tests: seed files load and parse without error."""

from pathlib import Path

from backend.app.knowledge.loader import (
    load_acb,
    load_beers,
    load_ddinter,
    load_sample_bundle,
)

SEEDS_DIR = Path(__file__).parent.parent / "seeds"


class TestSeedFilesExist:
    def test_ddinter_csv_present(self) -> None:
        assert (SEEDS_DIR / "ddinter.csv").exists()

    def test_acb_json_present(self) -> None:
        assert (SEEDS_DIR / "acb.json").exists()

    def test_beers_json_present(self) -> None:
        assert (SEEDS_DIR / "beers.json").exists()

    def test_sample_bundle_present(self) -> None:
        assert (SEEDS_DIR / "sample_bundle.json").exists()

    def test_sample_pdf_present(self) -> None:
        assert (SEEDS_DIR / "sample_clinical.pdf").exists()

    def test_sample_pdf_is_valid_pdf(self) -> None:
        with (SEEDS_DIR / "sample_clinical.pdf").open("rb") as fh:
            assert fh.read(4) == b"%PDF"


class TestDDInterLoads:
    def test_returns_nonempty_list(self) -> None:
        rows = load_ddinter()
        assert len(rows) > 0

    def test_required_keys_present(self) -> None:
        rows = load_ddinter()
        first = rows[0]
        assert {"drug_a", "drug_b", "level"} <= first.keys()

    def test_level_values_valid(self) -> None:
        valid_levels = {"Minor", "Moderate", "Major"}
        rows = load_ddinter()
        for row in rows[:100]:
            assert row["level"] in valid_levels, f"Unexpected level: {row['level']}"

    def test_no_empty_drug_names(self) -> None:
        rows = load_ddinter()
        for row in rows[:100]:
            assert row["drug_a"].strip(), "drug_a is empty"
            assert row["drug_b"].strip(), "drug_b is empty"

    def test_row_count(self) -> None:
        rows = load_ddinter()
        assert len(rows) == 10_000


class TestACBLoads:
    def test_has_source_field(self) -> None:
        data = load_acb()
        assert "source" in data
        assert data["source"]

    def test_has_drugs_list(self) -> None:
        data = load_acb()
        assert "drugs" in data
        assert len(data["drugs"]) > 0

    def test_drug_entries_have_required_fields(self) -> None:
        data = load_acb()
        for drug in data["drugs"]:
            assert "name" in drug
            assert "acb_score" in drug

    def test_acb_scores_in_valid_range(self) -> None:
        data = load_acb()
        for drug in data["drugs"]:
            assert drug["acb_score"] in (
                1,
                2,
                3,
            ), f"Invalid ACB score {drug['acb_score']} for {drug['name']}"


class TestBeersLoads:
    def test_has_source_field(self) -> None:
        data = load_beers()
        assert "source" in data
        assert "AGS" in data["source"] or "American Geriatrics" in data["source"]

    def test_has_rules_list(self) -> None:
        data = load_beers()
        assert "rules" in data
        assert len(data["rules"]) > 0

    def test_rules_have_required_fields(self) -> None:
        data = load_beers()
        for rule in data["rules"]:
            assert "id" in rule
            assert "drugs" in rule
            assert "recommendation" in rule
            assert "rationale" in rule
            assert isinstance(rule["drugs"], list)
            assert len(rule["drugs"]) > 0

    def test_warfarin_aspirin_interaction_present(self) -> None:
        data = load_beers()
        drug_drug_rules = [r for r in data["rules"] if r.get("interaction_type") == "drug-drug"]
        assert len(drug_drug_rules) > 0
        combined = " ".join(str(r) for r in drug_drug_rules)
        assert "warfarin" in combined.lower()
        assert "aspirin" in combined.lower()


class TestSampleBundleLoads:
    def test_resource_type_is_bundle(self) -> None:
        bundle = load_sample_bundle()
        assert bundle["resourceType"] == "Bundle"

    def test_has_entries(self) -> None:
        bundle = load_sample_bundle()
        assert len(bundle.get("entry", [])) > 0

    def test_has_patient_entry(self) -> None:
        bundle = load_sample_bundle()
        resource_types = {
            e.get("resource", {}).get("resourceType") for e in bundle.get("entry", [])
        }
        assert "Patient" in resource_types

    def test_has_medication_requests(self) -> None:
        bundle = load_sample_bundle()
        med_requests = [
            e
            for e in bundle.get("entry", [])
            if e.get("resource", {}).get("resourceType") == "MedicationRequest"
        ]
        assert len(med_requests) > 0

    def test_contains_warfarin_or_aspirin(self) -> None:
        bundle = load_sample_bundle()
        med_names = [
            e.get("resource", {}).get("medicationCodeableConcept", {}).get("text", "").lower()
            for e in bundle.get("entry", [])
            if e.get("resource", {}).get("resourceType") == "MedicationRequest"
        ]
        combined = " ".join(med_names)
        assert "warfarin" in combined or "aspirin" in combined


class TestDemoPatientSnapshots:
    """Golden tests for the DEMO-001 and DEMO-002 FHIR snapshot bundles."""

    SEEDS_DIR = Path(__file__).parent.parent / "seeds"

    def _load(self, filename: str) -> dict:
        import json

        return json.loads((self.SEEDS_DIR / filename).read_text())

    # ── file presence ────────────────────────────────────────────────────────

    def test_demo_001_snapshot_present(self) -> None:
        assert (self.SEEDS_DIR / "mock_fhir_snapshot.json").exists()

    def test_demo_002_snapshot_present(self) -> None:
        assert (self.SEEDS_DIR / "DEMO-002_fhir_snapshot.json").exists()

    # ── DEMO-001 bundle structure ────────────────────────────────────────────

    def test_demo_001_is_bundle(self) -> None:
        bundle = self._load("mock_fhir_snapshot.json")
        assert bundle["resourceType"] == "Bundle"

    def test_demo_001_has_patient(self) -> None:
        bundle = self._load("mock_fhir_snapshot.json")
        patients = [
            e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient"
        ]
        assert len(patients) == 1
        p = patients[0]
        assert p["id"] == "DEMO-001"
        assert p["gender"] == "female"
        assert p["birthDate"] < "1950-01-01", "Patient must be elderly (born before 1950)"

    def test_demo_001_has_three_medications(self) -> None:
        bundle = self._load("mock_fhir_snapshot.json")
        meds = [
            e["resource"]
            for e in bundle["entry"]
            if e["resource"]["resourceType"] == "MedicationStatement"
        ]
        assert len(meds) >= 3

    def test_demo_001_warfarin_rxcui_present(self) -> None:
        bundle = self._load("mock_fhir_snapshot.json")
        rxcuis = {
            coding["code"]
            for e in bundle["entry"]
            for coding in e["resource"].get("medicationCodeableConcept", {}).get("coding", [])
        }
        assert "11289" in rxcuis, "Warfarin RxCUI 11289 must be present"

    def test_demo_001_aspirin_rxcui_present(self) -> None:
        bundle = self._load("mock_fhir_snapshot.json")
        rxcuis = {
            coding["code"]
            for e in bundle["entry"]
            for coding in e["resource"].get("medicationCodeableConcept", {}).get("coding", [])
        }
        assert "1191" in rxcuis, "Aspirin RxCUI 1191 must be present"

    def test_demo_001_amitriptyline_rxcui_present(self) -> None:
        bundle = self._load("mock_fhir_snapshot.json")
        rxcuis = {
            coding["code"]
            for e in bundle["entry"]
            for coding in e["resource"].get("medicationCodeableConcept", {}).get("coding", [])
        }
        assert "703" in rxcuis, "Amitriptyline RxCUI 703 must be present"

    def test_demo_001_medications_have_dated_start(self) -> None:
        bundle = self._load("mock_fhir_snapshot.json")
        meds = [
            e["resource"]
            for e in bundle["entry"]
            if e["resource"]["resourceType"] == "MedicationStatement"
        ]
        dated = [m for m in meds if m.get("effectivePeriod", {}).get("start")]
        assert len(dated) >= 3, "All medications must have effectivePeriod.start"

    def test_demo_001_has_observation(self) -> None:
        bundle = self._load("mock_fhir_snapshot.json")
        obs = [
            e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation"
        ]
        assert len(obs) >= 1

    def test_demo_001_has_allergy(self) -> None:
        bundle = self._load("mock_fhir_snapshot.json")
        allergies = [
            e["resource"]
            for e in bundle["entry"]
            if e["resource"]["resourceType"] == "AllergyIntolerance"
        ]
        assert len(allergies) >= 1

    # ── DEMO-002 bundle structure ────────────────────────────────────────────

    def test_demo_002_is_bundle(self) -> None:
        bundle = self._load("DEMO-002_fhir_snapshot.json")
        assert bundle["resourceType"] == "Bundle"

    def test_demo_002_has_patient(self) -> None:
        bundle = self._load("DEMO-002_fhir_snapshot.json")
        patients = [
            e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient"
        ]
        assert len(patients) == 1
        assert patients[0]["id"] == "DEMO-002"
        assert patients[0]["gender"] == "male"

    def test_demo_002_has_nsaid(self) -> None:
        """DEMO-002 must include ibuprofen (the NSAID for triple-whammy AKI risk)."""
        bundle = self._load("DEMO-002_fhir_snapshot.json")
        rxcuis = {
            coding["code"]
            for e in bundle["entry"]
            for coding in e["resource"].get("medicationCodeableConcept", {}).get("coding", [])
        }
        assert "5640" in rxcuis, "Ibuprofen RxCUI 5640 must be present in DEMO-002"

    def test_demo_002_has_ace_inhibitor(self) -> None:
        bundle = self._load("DEMO-002_fhir_snapshot.json")
        rxcuis = {
            coding["code"]
            for e in bundle["entry"]
            for coding in e["resource"].get("medicationCodeableConcept", {}).get("coding", [])
        }
        assert "29046" in rxcuis, "Lisinopril RxCUI 29046 must be present in DEMO-002"
