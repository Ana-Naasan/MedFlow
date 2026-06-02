#!/usr/bin/env python
"""Manual test: run the full reasoning pipeline against the live Gemini API.

Usage:
    source .venv/bin/activate
    python mini-tests/manual_gemini_reasoning.py [drug_name]

Examples:
    python mini-tests/manual_gemini_reasoning.py                    # Metformin (default)
    python mini-tests/manual_gemini_reasoning.py lisinopril
    python mini-tests/manual_gemini_reasoning.py 197885             # by RxCUI
    python mini-tests/manual_gemini_reasoning.py metformin          # explicit

Requires GOOGLE_GENAI_API_KEY in .env (should be set already).
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.fhir.flatten import flatten_to_tagged_text
from backend.app.knowledge.openfda import lookup_drug
from backend.app.reasoning.core import run_reasoning


async def main() -> None:
    # ── 1. Parse drug argument ─────────────────────────────────────────────
    drug_input = sys.argv[1] if len(sys.argv) > 1 else "metformin"
    rxcui = drug_input if drug_input.isdigit() else None
    generic_name = drug_input if not rxcui else None

    print(f"Drug input: {drug_input} (rxcui={rxcui}, name={generic_name})")

    # ── 2. Check API key ───────────────────────────────────────────────────
    api_key = os.environ.get("GOOGLE_GENAI_API_KEY")
    if not api_key:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GOOGLE_GENAI_API_KEY="):
                    api_key = line.split("=", 1)[1]
                    os.environ["GOOGLE_GENAI_API_KEY"] = api_key
                    break

    if not api_key:
        print("❌ GOOGLE_GENAI_API_KEY not set in .env")
        print("   Add it: echo 'GOOGLE_GENAI_API_KEY=AIza...' >> .env")
        sys.exit(1)

    # ── 3. Load demo patient ───────────────────────────────────────────────
    snap_path = Path("backend/app/seeds/mock_fhir_snapshot.json")
    if not snap_path.exists():
        print(f"❌ Snapshot not found at {snap_path}")
        sys.exit(1)

    snap = json.loads(snap_path.read_text())
    resources = [entry["resource"] for entry in snap["entry"]]
    flattened = flatten_to_tagged_text(resources)

    print()
    print("=" * 72)
    print("PATIENT FLATTENED TEXT")
    print("=" * 72)
    print(flattened)
    print()

    # ── 4. Fetch OpenFDA evidence ──────────────────────────────────────────
    print("=" * 72)
    print(f"FETCHING OpenFDA EVIDENCE FOR '{drug_input}'...")
    print("=" * 72)
    result = await lookup_drug(rxcui=rxcui, generic_name=generic_name)
    if result is None:
        print(f"❌ No OpenFDA results for '{drug_input}'")
        sys.exit(1)

    print(f"Drug: {result.generic_name} ({result.brand_name})")
    print(f"Evidence snippets: {len(result.evidence_snippets)}")
    for s in result.evidence_snippets:
        print(f"  [{s.id}] {s.label[:120]}")
    print()

    # ── 5. Run Gemini reasoning ────────────────────────────────────────────
    print("=" * 72)
    print("CALLING GEMINI (gemini-2.5-flash)...")
    print("=" * 72)

    try:
        hypotheses = await run_reasoning(flattened, result.evidence_snippets)
    except Exception as e:
        print(f"❌ Gemini call failed: {type(e).__name__}: {e}")
        sys.exit(1)

    # ── 6. Print results ───────────────────────────────────────────────────
    print()
    print("=" * 72)
    print(f"RESULTS: {len(hypotheses)} verified hypotheses")
    print("=" * 72)

    if not hypotheses:
        print("  (no hypotheses survived verification)")
        print()
        print("This could mean:")
        print("  - Gemini returned empty or abstained")
        print("  - Citations didn't match patient tags")
        print("  - A network/API error occurred (check above)")
        sys.exit(0)

    for i, h in enumerate(hypotheses, 1):
        print()
        print(f"── Hypothesis {i} ──────────────────────────────────────")
        print(f"  Title:      {h.title}")
        print(f"  Severity:   {h.severity}")
        print(f"  Confidence: {h.confidence}")
        print(f"  Why:        {h.why[:300]}...")
        print(f"  Citations ({len(h.citations)}):")
        for c in h.citations:
            print(f"    • [{c.kind}] {c.ref} — {c.label}")

    print()
    print("✅ Done.")


if __name__ == "__main__":
    asyncio.run(main())
