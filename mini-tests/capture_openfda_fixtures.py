#!/usr/bin/env python
"""Capture real OpenFDA API responses and write them as JSON fixtures."""
import asyncio
import json
import sys
from pathlib import Path

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.knowledge.openfda import _get_json

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "backend" / "app" / "tests" / "fixtures"


async def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    # Event fixture for lisinopril (RxCUI 197885)
    body = await _get_json("event", "patient.drug.openfda.rxcui:197885", 2)
    fix = FIXTURE_DIR / "openfda_event_197885.json"
    fix.write_text(json.dumps(body, indent=2))
    print(f"Written: {fix} ({len(fix.read_text())} bytes)")

    # Label fixture for lisinopril (generic name)
    body = await _get_json("label", 'openfda.generic_name:"lisinopril"', 1)
    fix = FIXTURE_DIR / "openfda_label_lisinopril.json"
    fix.write_text(json.dumps(body, indent=2))
    print(f"Written: {fix} ({len(fix.read_text())} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
