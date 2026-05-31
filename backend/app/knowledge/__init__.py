"""Drug-knowledge layer for Umraa.

Exposes loaders for vendored seed datasets:
  load_ddinter()      — DDInter 2.0 drug-interaction pairs
  load_acb()          — Anticholinergic Cognitive Burden scale
  load_beers()        — AGS 2023 Beers Criteria rules
  load_sample_bundle() — Synthea synthetic FHIR R4 bundle
"""

from backend.app.knowledge.loader import (
    load_acb,
    load_beers,
    load_ddinter,
    load_sample_bundle,
)

__all__ = ["load_ddinter", "load_acb", "load_beers", "load_sample_bundle"]
