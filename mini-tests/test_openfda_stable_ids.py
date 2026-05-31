#!/usr/bin/env python
"""Manual test: verify that OpenFDA evidence-snippet stable IDs are
reproducible across cached and uncached calls to ``lookup_drug``.

Usage
-----
From the project root::

    source .venv/bin/activate
    python mini-tests/test_openfda_stable_ids.py 197885        # by RxCUI
    python mini-tests/test_openfda_stable_ids.py lisinopril    # by generic name
    python mini-tests/test_openfda_stable_ids.py               # interactive

What this tests
---------------
* ``lookup_drug`` returns an ``OpenFdaResult`` with evidence snippets.
* Each snippet has a deterministic ``id`` (e.g.
  ``openfda:197885:adverse_events:total_count``).
* The same IDs appear on the **first** (API) call and the **second**
  (cached) call — proving stability across runs.
"""

import asyncio
import sys

from backend.app.knowledge.openfda import lookup_drug


async def main(query: str) -> None:
    rxcui = query if query.isdigit() else None
    generic_name = query if not rxcui else None

    print(f"\nQuery: {query}\n")

    # Call 1 — real API (or cached if already seen)
    r1 = await lookup_drug(rxcui=rxcui, generic_name=generic_name)
    if r1 is None:
        print("No results.")
        return

    ids_1 = {s.id for s in r1.evidence_snippets}
    print(f"Call 1 — {len(r1.evidence_snippets)} snippets:")
    for s in r1.evidence_snippets:
        print(f"  {s.id}")

    # Call 2 — guaranteed cached, IDs must match
    r2 = await lookup_drug(rxcui=rxcui, generic_name=generic_name)
    ids_2 = {s.id for s in r2.evidence_snippets}

    print(f"\nCall 2 — {len(r2.evidence_snippets)} snippets:")
    for s in r2.evidence_snippets:
        print(f"  {s.id}")

    if ids_1 == ids_2:
        print(f"\n✅ Stable IDs match across calls ({len(ids_1)} unique IDs)")
    else:
        print("\n❌ IDs differ!")
        print(f"  Only in call 1: {ids_1 - ids_2}")
        print(f"  Only in call 2: {ids_2 - ids_1}")

    print("\nEvidence label preview:")
    for s in r1.evidence_snippets:
        print(f"  [{s.id}] {s.label[:120]}…")


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else input("RxCUI or generic name: ").strip()
    asyncio.run(main(query))
