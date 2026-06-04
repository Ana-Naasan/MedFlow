"""Drug-knowledge layer for MedFlow.

Exposes loaders for vendored seed datasets:
  load_ddinter()      — DDInter 2.0 drug-interaction pairs
  load_acb()          — Anticholinergic Cognitive Burden scale
  load_beers()        — AGS 2023 Beers Criteria rules
  load_sample_bundle() — Synthea synthetic FHIR R4 bundle

And lookup functions for age-aware drug-safety checks:
  lookup_beers()      — Beers 2023 criteria (age-gated ≥65)
  lookup_acb()        — ACB burden score
"""

from backend.app.knowledge.acb import AcbMatch, AcbResult, lookup_acb
from backend.app.knowledge.beers import BeersMatch, BeersResult, lookup_beers
from backend.app.knowledge.loader import (
    load_acb,
    load_beers,
    load_ddinter,
    load_sample_bundle,
)

__all__ = [
    "load_ddinter",
    "load_acb",
    "load_beers",
    "load_sample_bundle",
    "lookup_beers",
    "BeersMatch",
    "BeersResult",
    "lookup_acb",
    "AcbMatch",
    "AcbResult",
]
