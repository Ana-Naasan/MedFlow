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
