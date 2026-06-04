# Data Sources

MedFlow runs entirely on **synthetic patient data** and **publicly available reference
datasets**. No real patient data is used anywhere in the repository or the reasoning
path.

For how these sources become deterministic, cited evidence cards behind every
hypothesis, see [`docs/CAPABILITIES.md`](./CAPABILITIES.md).

## Vendored knowledge datasets

These ship in `backend/app/seeds/`. Full provenance, retrieval URLs, licenses, and
citations are documented in [`backend/app/seeds/SOURCES.md`](../backend/app/seeds/SOURCES.md).

| File | What | Source | License / use |
|---|---|---|---|
| `ddinter.csv` | Drug-drug interaction pairs (subset, 10,000 rows) | [DDInter 2.0](https://ddinter.scbdd.com) | Academic / non-commercial; cite *Nucleic Acids Research* 2022;50:D1200 |
| `acb.json` | Anticholinergic Cognitive Burden scale (scored drug list) | Carnahan et al., *J Clin Pharmacol* 2006 | Published research, reproduced for educational/CDS use |
| `beers.json` | AGS 2023 Beers Criteria (representative subset) | American Geriatrics Society 2023 | © AGS; reproduced for educational/CDS use |
| `sample_bundle.json` | Synthetic FHIR R4 patient bundle | [Synthea sample data](https://github.com/synthetichealth/synthea-sample-data) | Apache-2.0; synthetic, not real PHI |
| `sample_clinical.pdf` | Synthetic discharge summary with a planted interaction | Generated (`fpdf2`) on the Synthea patient | Synthetic, no copyright |

## External runtime services

Reasoning and drug-knowledge enrichment call these at request time. All degrade
gracefully, a missing key or an unreachable service yields fewer evidence cards rather
than a failed request, and CI runs against recorded fixtures rather than the live APIs.

| Service | Used for | Auth |
|---|---|---|
| **RxNav / RxNorm** (NLM) | Normalize medications to RxCUI + ingredient + ATC | none |
| **openFDA** | Single-drug adverse-reaction (FAERS) + label lookup | optional `OPENFDA_API_KEY` (raises rate limits) |
| **Google Gemini** (`google-genai`) | The reasoning call over the tagged, closed-world context | `GOOGLE_GENAI_API_KEY` |

## Why no vector database

A single patient's record fits whole in the model context, and the knowledge joins are
exact key lookups (RxCUI, ATC, drug-pair). Similarity search would *guess* where an exact
join is a *fact*, so retrieval is deliberately out of scope, every knowledge claim is an
exact, citable lookup.
