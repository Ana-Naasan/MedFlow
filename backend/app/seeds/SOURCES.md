# Seed Data Sources

All files in this directory are either publicly downloadable reference datasets or
synthetic data generated for development purposes. No real patient data is used.

---

## ddinter.csv

- **What**: Drug-drug interaction pairs from the DDInter 2.0 database.
  First 10,000 rows sampled from all ATC-code files (A–V), combined and trimmed.
- **Source**: DDInter — <https://ddinter.scbdd.com>
- **Download URL**: `https://ddinter.scbdd.com/static/media/download/ddinter_downloads_code_{A-V}.csv`
- **Retrieved**: 2026-05-30
- **Licence**: Free for academic / non-commercial use. Cite:
  Yang H, et al. "DDInter: an online drug-drug interaction database towards
  improving clinical decision-making and patient safety." *Nucleic Acids Research*
  2022;50:D1200–D1207. <https://doi.org/10.1093/nar/gkab880>
- **Columns**: `DDInterID_A, Drug_A, DDInterID_B, Drug_B, Level`
- **Level values**: `Minor`, `Moderate`, `Major`
- **Row count**: 10,000 (subset; full dataset ≈507,000 pairs across all ATC codes)

---

## acb.json

- **What**: Anticholinergic Cognitive Burden (ACB) scale — scored drug list (1–3).
- **Source**: Carnahan RM, Lund BC, Perry PJ, Pollock BG, Culp KR.
  "The Anticholinergic Drug Scale as a Measure of Drug-Related Anticholinergic Burden."
  *J Clin Pharmacol* 2006;46(12):1481–1486.
  <https://doi.org/10.1177/0091270006292126>
- **Retrieved**: 2026-05-30 (transcribed from published table)
- **Licence**: Published research; data reproduced for educational/clinical decision support.
- **Score interpretation**:
  - `1` = Possible anticholinergic properties
  - `2` = Clinically relevant anticholinergic properties
  - `3` = Markedly anticholinergic (high burden)
- **Drug count**: ~70 representative entries (not exhaustive)

---

## beers.json

- **What**: AGS 2023 Beers Criteria — rules for potentially inappropriate medication
  use in adults aged 65+. Representative subset of key criteria.
- **Source**: 2023 American Geriatrics Society Beers Criteria Update Expert Panel.
  "American Geriatrics Society 2023 Updated AGS Beers Criteria for Potentially
  Inappropriate Medication Use in Older Adults."
  *J Am Geriatr Soc* 2023;71(7):2052–2081.
  <https://doi.org/10.1111/jgs.18372>
- **Retrieved**: 2026-05-30 (transcribed from published criteria)
- **Licence**: Copyright American Geriatrics Society. Reproduced for clinical
  decision support / educational purposes. See full publication for complete list.
- **Rule count**: 23 rules across anticholinergics, cardiovascular, CNS, endocrine,
  GI, pain, sleep, and drug-drug interaction categories.

---

## sample_bundle.json

- **What**: Synthetic FHIR R4 patient bundle — older adult male with cardiac/HTN
  medications (aspirin, metoprolol, lisinopril, hydrochlorothiazide, amlodipine,
  pravastatin, prasugrel, nitroglycerin). Trimmed to clinically-relevant resource types.
  NOTE: the warfarin + aspirin planted interaction is NOT in this bundle — it lives in
  `sample_clinical.pdf` and Beers rule `beers-2023-interaction-01`. This bundle's own
  antiplatelet pairing for demo purposes is aspirin + prasugrel.
- **Source**: Synthea synthetic patient generator — synthetichealth/synthea-sample-data
  GitHub repository.
  <https://github.com/synthetichealth/synthea-sample-data>
- **Downloaded from**: `https://raw.githubusercontent.com/synthetichealth/synthea-sample-data/master/downloads/latest/synthea_sample_data_fhir_latest.zip`
- **Retrieved**: 2026-05-30
- **Licence**: Apache License 2.0. NOT real patient data.
- **Resource types retained**: Patient, Condition, MedicationRequest, Observation,
  Procedure, Encounter (425 entries; original 735 entries trimmed).
- **Original file**: `Kent912_Wiza601_25127bd5-f9aa-30d5-d3f9-c5c88e27d527.json`

---

## sample_clinical.pdf

- **What**: Synthetic discharge medication summary for a fictitious older adult male
  patient (Kent Romaguera, DOB 1940). Includes a planted warfarin + aspirin drug
  interaction alert referencing the AGS 2023 Beers Criteria.
- **Source**: Generated synthetically with the `fpdf2` library, based on the Synthea
  patient above. The one-off generator script is not committed; the PDF is vendored as a
  frozen demo artifact (regenerate only if the planted-interaction text needs to change).
- **Generated**: 2026-05-30
- **Licence**: Synthetic data, no copyright. NOT real patient data.
- **Purpose**: Demo input for issue #27 (PDF clinical connector). Text is
  extractable (not scanned) — `pdfplumber` can read it.
- **Planted interaction**: Warfarin (anticoagulant) + Aspirin 81 mg (antiplatelet)
  flagged per Beers rule `beers-2023-interaction-01`.
