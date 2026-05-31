"""Load vendored drug-knowledge seed files from backend/app/seeds/."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

_SEEDS: Path = Path(__file__).parent.parent / "seeds"


def load_ddinter() -> list[dict[str, str]]:
    """Return DDInter interaction rows normalised to drug_a/drug_b/level keys.

    Source: DDInter 2.0 (https://ddinter.scbdd.com).
    Level values: Minor | Moderate | Major.
    """
    with (_SEEDS / "ddinter.csv").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [
            {
                "drug_a": row["Drug_A"],
                "drug_b": row["Drug_B"],
                "level": row["Level"],
                "ddinter_id_a": row["DDInterID_A"],
                "ddinter_id_b": row["DDInterID_B"],
            }
            for row in reader
        ]


def load_acb() -> dict[str, Any]:
    """Return ACB scale data dict with 'source' and 'drugs' keys.

    Source: Carnahan et al. 2006 ACB Scale.
    Each drug entry has: name, rxcui, acb_score (1–3).
    """
    return json.loads((_SEEDS / "acb.json").read_text(encoding="utf-8"))


def load_beers() -> dict[str, Any]:
    """Return AGS 2023 Beers Criteria dict with 'source' and 'rules' keys.

    Source: AGS 2023 Beers Criteria (https://doi.org/10.1111/jgs.18372).
    """
    return json.loads((_SEEDS / "beers.json").read_text(encoding="utf-8"))


def load_sample_bundle() -> dict[str, Any]:
    """Return the synthetic Synthea FHIR R4 Bundle dict.

    Source: Synthea synthetic patient generator (not real patient data).
    resourceType is 'Bundle', entries include Patient, Condition,
    MedicationRequest, Observation, Procedure, Encounter.
    """
    return json.loads((_SEEDS / "sample_bundle.json").read_text(encoding="utf-8"))
