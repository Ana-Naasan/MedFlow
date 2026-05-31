# Mini-Tests

This directory contains short manual scripts for testing different
portions of the API. These are **not** pytest tests — they are meant to
be run directly from the terminal during development.

## How to run

Activate the virtual environment first, then run any script:

```bash
source .venv/bin/activate
python mini-tests/<script_name>.py [args]
```

## Available scripts

| Script | Purpose |
|---|---|
| `test_openfda_stable_ids.py` | Verify OpenFDA evidence-snippet IDs are deterministic across API + cache calls |
| `capture_openfda_fixtures.py` | Capture live API responses as JSON test fixtures under ``backend/app/tests/fixtures/`` |

## Adding a new script

1. Create a `.py` file in this directory.
2. Make it runnable directly (`if __name__ == "__main__": ...`).
3. Document it in this README table.
4. These files are intentionally **not** gitignored so they serve as
discoverable documentation of how the API is used.
