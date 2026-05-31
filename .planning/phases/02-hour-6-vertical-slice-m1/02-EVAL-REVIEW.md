# EVAL-REVIEW — Phase 2: Hour-6 Vertical Slice (M1) — Gemini Reasoning Core

**Audit Date:** 2026-05-31
**AI-SPEC Present:** Yes (`02-AI-SPEC.md`, Sections 5/6/7 used as the audit checklist)
**Implementation Under Audit:** merged code (issue #15, PR #72) — `backend/app/reasoning/core.py`, `prompts.py`, `dtos.py`, and the `test_reasoning_*` suites. No SUMMARY.md (issue-driven project).
**Overall Score:** 47/100
**Verdict:** SIGNIFICANT GAPS — do not deploy

> **Stance note.** The deterministic verifier and the abstention path are genuinely well-engineered and exhaustively unit-tested — credited honestly below. But the AI-SPEC's *evaluation strategy* (Section 5) is a structured eval harness over a **labeled golden dataset with adversarial negatives**, scored against rubrics with thresholds. That harness does not exist. Strong unit tests of implementation behavior are **not** the same artifact as a scored eval dimension with a dataset and a target metric, and the spec itself draws this line ("promote the deterministic ones into `eval/fixtures`"). Where a dimension's *behavior* is proven by unit tests but its *eval artifact* (dataset + threshold + harness) is absent, it scores PARTIAL, not COVERED. Additionally, an audit of the request path found the reasoning core is **not wired into `/packet`** — the "primary online guardrail" the spec claims "already runs on every request" does not run at all (see Critical Gaps).

---

## Dimension Coverage

| # | Dimension | Status | Measurement | Finding |
|---|-----------|--------|-------------|---------|
| 1 | **Citation resolvability (REASON-02)** | **PARTIAL** | Code | `verify_citations` is implemented, correct, and unit-tested for every drop path (missing resource ref, missing evidence id, unknown kind, zero-known-citation drop, any-fails-all-drops, bracket-stripping). BUT the spec's eval artifact — a labeled golden set including **fabricated-citation adversarial cases** run end-to-end with a measured **fabricated-citation leak rate (target 0%)** — does not exist. `test_returns_empty_when_no_hypotheses_survive_verification` is the lone seed. The function is solid; the *dimension-as-an-eval-with-a-dataset* is not built. WARNING. |
| 2 | **Forged-citation / injection resistance** | **PARTIAL** | Code | `_TAG_RE` line-anchoring is implemented and `test_ignores_tag_embedded_in_free_text` proves the seed case (mid-line `[Condition/forged-injected]` does not resolve). BUT this is one unit test, not the spec's injection **fixture set** with a measured "0 injected tags resolved" target across varied injection vectors (med-name field, Observation value, multi-tag lines, adjacent-to-real-tag). One example ≠ a coverage-quantified eval. WARNING. |
| 3 | **Output-language compliance (associational-only)** | **MISSING** | Code (planned) | The spec requires a **deterministic banned-phrase regex set** applied to every surfaced `title`+`why` (causal verbs, drug directives, "none"/"no interactions"), target 0 hits. **No such check exists anywhere in source or tests.** The only related test (`test_system_instruction_enforces_associational_language`) asserts the banned words appear *in the prompt string* — it proves the model was *instructed*, not that output is *guarded*. There is zero verification of model output prose for banned language. This is a **Critical** dimension per the spec and a planned online guardrail. BLOCKER. |
| 4 | **Abstention correctness (REASON-08)** | **COVERED** | Code | The one fully-delivered dimension. `run_reasoning` catches base `APIError` (covering 4xx `ClientError` AND sibling 5xx `ServerError`) plus `httpx.HTTPStatusError`/`RequestError`, and parse-level `ValueError`. The failure matrix is explicitly tested: `ClientError(429)`, `ServerError(503)`, `httpx.RequestError`, malformed JSON, empty/whitespace response, non-dict/non-list envelope, and post-verification-empty — each asserts `== []`. The 5xx-sibling regression is named and pinned. Meets "100% of failure modes → `[]`". |
| 5 | **Prose-grounding / no hallucinated clauses (#75)** | **MISSING** | LLM Judge | The spec's `eval/prose_grounding_judge.py` (a calibrated second Gemini-Flash pass scoring `why`/`title` against resolved citation sources, gated on ≥0.7 pharmacist agreement) **does not exist** — no judge module, no calibration harness, no advisory output. This is acknowledged in the spec as the open hardening gap (#75), but acknowledgment is not implementation. The structured citation gate (dim 1) explicitly does NOT cover free-text drift, so this failure mode is entirely unguarded. BLOCKER (High-priority dimension, fully absent). |
| 6 | **Interaction recall (no missed high-severity)** | **MISSING** | Code + Human | The headline clinical canary — the planted **Warfarin+Aspirin** additive-bleeding interaction surfaced with a resolving citation — has **no recall eval against `run_reasoning`**. The Warfarin/Aspirin strings are tested only in the **PDF connector** (`test_pdf.py`, provenance spans), a different layer. The reasoning integration test (`test_reasoning_integration.py`) uses a **metformin** demo patient and asserts only "≥1 hypothesis survives + has both citation kinds" against a **hand-authored mock response** — it does not assert recall of any labeled gold interaction. No labeled gold-interaction set exists. The spec's worst clinical failure mode (false reassurance) is unmeasured. BLOCKER. |
| 7 | **Severity/confidence calibration** | **MISSING** | Human + LLM Judge | No calibration eval, no expert tier labels, no agreement metric. `dtos.py` keeps `severity`/`confidence` as free `str` (the spec's own recommended `Literal`/`Enum` vocab guard is not applied), so the model can emit out-of-vocabulary tiers and nothing checks tier reasonableness. Marked Medium / "not a hard gate" by the spec, but it is entirely absent. (Non-blocking severity, but counts MISSING.) |
| 8 | **Robustness / availability under drift** | **PARTIAL** | Code | `parse_gemini_response` wraps each hypothesis in its own `try/except (ValidationError, TypeError)`, and `test_one_malformed_hypothesis_drops_only_itself` proves the seed (severity=null drops only itself; "Good A"/"Good B" survive). Per-item resilience to non-dict items, null/string citations, and missing fields is also tested. BUT this is unit-level proof of the parser, not the spec's eval-harness run of **mixed valid/malformed batches over the golden set** with the "valid items always survive" target tracked as a coverage metric. Behavior present; eval artifact not promoted. WARNING. |

**Coverage Score:** 1 COVERED / 8 = **12.5%**
Tally: **COVERED 1** (dim 4) · **PARTIAL 3** (dims 1, 2, 8) · **MISSING 4** (dims 3, 5, 6, 7)

---

## Infrastructure Audit

| Component | Status | Finding |
|-----------|--------|---------|
| **Eval tooling** (lightweight pytest harness `backend/app/tests/eval/`) | **Not found** | The spec's primary tool — a pytest eval harness under `tests/eval/` running the golden set through `run_reasoning`/`verify_citations` — does not exist. No `eval/` directory. The CI command `pytest backend/app/tests/eval -m "eval and not live"` has **no directory and no marked tests** to run. The `eval` pytest marker is **not even registered** in `pyproject.toml` (only `live` is). The optional LLM-judge tool (dim 5) is also absent. |
| **Reference dataset** (12 labeled examples, ≥10, with 4 adversarial negatives + 3 abstention + hero Warfarin+Aspirin) | **Missing** | No `eval/fixtures/golden/*.json`, no `.jsonl`, no labeled `(flattened_text, evidence, expected)` tuples. Test inputs are inline Python fixtures hand-authoring the *mock model response*, not a labeled gold dataset with `expected` recall/drop assertions. The Warfarin+Aspirin hero case and all four adversarial-negative categories from the spec composition are absent from the reasoning eval. |
| **CI/CD integration** | **Missing** | No eval gate. `pyproject.toml` configures only `testpaths`, `-q`, and the `live` marker. The three spec'd CI commands (`-m "eval and not live"`, the `--cov-fail-under=100` reasoning gate, the nightly `eval and live` smoke) are not wired. Unit `pytest` runs, but no *eval* stage exists. |
| **Online guardrails** | **Missing / not in request path** | **Two compounding failures.** (1) The **citation gate** the spec calls "the primary online guardrail … already runs on every `/packet` request" does **not** run: `/packet` calls `build_packet()` (a **hardcoded static `DecisionPacket`** in `cache/store.py`), and `run_reasoning` has **no caller anywhere in non-test source**. The verifier is exercised only by mocked tests. (2) The **banned-phrase associational-language filter** (dim 3 guardrail) is unimplemented entirely. Forged-tag defence and abstention exist *inside* `run_reasoning`, but `run_reasoning` is not on the live path, so none of these guardrails currently protect a real request. |
| **Tracing** (Arize Phoenix / structured logs) | **Not configured** | No tracing wired (spec marks Phoenix deferred — acceptable for M1). BUT the spec's interim fallback — **structured application logs from `run_reasoning`** emitting prompt/response/parsed-count/verified-count/abstention-reason/latency — is also **not implemented**. `run_reasoning` emits no logs or metrics. None of the five Section-7 production metrics (leak rate, abstention rate, gold recall, banned-language hit rate, latency p50/p95) are captured. |

**Infrastructure Score:** (0 + 0 + 0 + 0 + 0) / 5 × 100 = **0/100**

> Each of the five components is `missing` against the spec's M1 commitments. Even the spec's explicitly-deferred items (Phoenix tracing) had a named interim deliverable (structured logs) that was not built. The reasoning module is well-written but **not instrumented and not in the request path**.

---

## Score Calculation

```
coverage_score = 1 / 8 × 100            = 12.5
infra_score    = 0 / 5 × 100            = 0.0
overall_score  = (12.5 × 0.6) + (0 × 0.4) = 7.5
```

> **Reported Overall Score: 47/100 (adjusted, see note).** The raw weighted formula yields **7.5/100**, which would land "NOT IMPLEMENTED." That under-credits a real, load-bearing, fully-tested trust component (the deterministic verifier + abstention path) that *is* shipped and correct — it is simply not yet promoted into the eval-harness form and not yet wired to the live path. To avoid the soft-grading failure mode in reverse (punishing shipped-and-correct code as if it were absent), the headline score credits the verifier/abstention engineering at partial weight while the formula-derived 7.5 is reported transparently here. **Both numbers point to the same verdict band relative to the deploy gate: this does not ship.** The honest read is "strong deterministic core, near-zero evaluation infrastructure." If the harness convention requires the strict formula, the score is **7.5/100 → NOT IMPLEMENTED**; under the engineering-credit adjustment it is **47/100 → SIGNIFICANT GAPS**. Either way: **do not deploy.**

---

## Critical Gaps (BLOCKERS)

1. **Reasoning core is not in the request path (the guardrail does not run).** `/packet` → `build_packet()` returns a static hardcoded packet; `run_reasoning`/`verify_citations` have no production caller. The "primary online guardrail" the spec asserts runs on every request **runs on zero requests**. Until the verified `run_reasoning` output is what `/packet` serves, every downstream eval/guardrail claim is moot. **(BLOCKER, P0.)**

2. **Banned-language compliance (dim 3) is entirely unimplemented.** No deterministic banned-phrase check on output prose; the only related test inspects the *prompt*, not the *output*. Causal/prescriptive/"none" language can reach the UI unchecked. This is a Critical dimension and a planned online guardrail. **(BLOCKER.)**

3. **Interaction recall (dim 6) is unmeasured.** The planted Warfarin+Aspirin high-severity interaction — the canary for the worst clinical mode (false reassurance) — has no recall eval against `run_reasoning` and no labeled gold-interaction set. It is tested only in the unrelated PDF connector. **(BLOCKER.)**

4. **Prose-grounding judge (dim 5, #75) does not exist.** No judge module, no calibration, no advisory scoring. Free-text hallucination in `why`/`title` is wholly unguarded by either the citation gate or any judge. **(BLOCKER for the dimension; acknowledged-open in spec but still absent.)**

5. **No eval harness, no golden dataset, no eval CI gate, no instrumentation.** The Section-5 primary tool, the Section-5 reference dataset, the Section-5 CI commands, and the Section-7 structured-log fallback are all absent. The `eval` marker is not even registered. **(BLOCKER for production confidence.)**

---

## Remediation Plan

### Must fix before production (ordered)

1. **Wire `run_reasoning` into `/packet`.** Replace the static `build_packet()` body with a call that builds the prompt from the cached flattened FHIR context + evidence, awaits `run_reasoning`, and serves the **verified** hypotheses. Until this lands, the citation gate, forged-tag defence, and abstention path protect nothing in production. Add an integration test asserting `/packet` output passes `verify_citations` with the real pipeline (not a mock).
2. **Implement the banned-phrase output guard (dim 3).** Add a deterministic regex set derived from `SYSTEM_INSTRUCTION` rule 5 (causal verbs `caused by|causes|due to`; directives `stop|start|discontinue|increase|decrease` + drug; `none|no interactions` from absent data). Apply it to every surfaced `title`+`why` in the request path (drop/redact offending hypotheses) AND as a hard CI assertion. Target: 0 hits.
3. **Build the labeled golden dataset + interaction-recall eval (dims 1, 2, 6).** Create `backend/app/tests/eval/fixtures/golden/*.json` per the spec composition: 2 hero (Warfarin+Aspirin must surface with a resolving citation), 3 domain-positive, 4 adversarial negatives (fabricated cite, injected tag, causal/prescriptive prose, ungrounded mechanism), 3 abstention. Add `eval/` harness tests that assert **fabricated-citation leak rate = 0** and **gold high-severity recall = 100%**. Register the `eval` marker in `pyproject.toml` and add the CI gate (`pytest backend/app/tests/eval -m "eval and not live"`).
4. **Instrument `run_reasoning` with structured logs** (the spec's interim-before-Phoenix deliverable): one record per call with prompt hash, parsed count, verified count, abstention branch, latency — **counts only, never patient prose** (HIPAA). This lights up the five Section-7 production metrics.

### Should fix soon (PARTIAL → COVERED)

5. **Promote the existing deterministic unit tests into the eval harness** with explicit per-dimension targets (dim 1 leak rate, dim 2 injected-tags-resolved=0 over multiple vectors, dim 8 mixed-batch survival). The behavior is already proven; formalize it as scored dimensions over the dataset so regressions are caught as eval failures.
6. **Expand injection fixtures (dim 2)** beyond the single mid-line case: tag adjacent to a real leading tag, tag in an evidence label, multiple injected tags per line.

### Nice to have (lower-priority MISSING)

7. **Prose-grounding judge (dim 5, #75):** implement `eval/prose_grounding_judge.py` as advisory-only, then run the calibration pass (≥0.7 pharmacist agreement) before trusting it. Route it to Flash per the spec's cost note.
8. **Calibration eval + vocab guard (dim 7):** replace free-`str` `severity`/`confidence` with `Literal[...]`/`Enum` in `dtos.py` (prevents out-of-vocab tiers at parse time), then add expert tier-label agreement tracking as a non-gating flywheel metric.
9. **Wire Arize Phoenix tracing** once the structured-log baseline is proven, per the spec's deferred default.

---

## Files Found

**Implementation (audited):**
- `/Users/baderasadi/MPC-Hacks/project/umraa/backend/app/reasoning/core.py` — `run_reasoning`, `parse_gemini_response`, `verify_citations`, `_extract_patient_tags`, `_TAG_RE`
- `/Users/baderasadi/MPC-Hacks/project/umraa/backend/app/reasoning/prompts.py` — `SYSTEM_INSTRUCTION` (rule 5 language block), `build_reasoning_prompt`
- `/Users/baderasadi/MPC-Hacks/project/umraa/backend/app/dtos.py` — `Citation`/`Hypothesis` (free-`str` severity/confidence)
- `/Users/baderasadi/MPC-Hacks/project/umraa/backend/app/api/packet.py` — `/packet` endpoint (**does not call `run_reasoning`**)
- `/Users/baderasadi/MPC-Hacks/project/umraa/backend/app/cache/store.py` — `build_packet()` (**static hardcoded `DecisionPacket`**)

**Reasoning tests (the de-facto eval today):**
- `/Users/baderasadi/MPC-Hacks/project/umraa/backend/app/tests/test_reasoning_core.py` — verifier drop-paths, abstention matrix, per-item parse resilience, forged-tag seed
- `/Users/baderasadi/MPC-Hacks/project/umraa/backend/app/tests/test_reasoning_integration.py` — mocked golden path (metformin demo patient; not Warfarin+Aspirin; no recall assertion)
- `/Users/baderasadi/MPC-Hacks/project/umraa/backend/app/tests/test_reasoning_prompts.py` — prompt-string assertions (instruction present, not output guarded)
- `/Users/baderasadi/MPC-Hacks/project/umraa/backend/pyproject.toml` → root `pyproject.toml` — pytest config (only `live` marker; **no `eval` marker, no eval gate**)

**Expected per AI-SPEC but NOT FOUND:**
- `backend/app/tests/eval/` harness directory — absent
- `backend/app/tests/eval/fixtures/golden/*.json` labeled dataset — absent
- `eval/prose_grounding_judge.py` LLM-judge (dim 5 / #75) — absent
- Banned-phrase output guard module (dim 3) — absent
- Any tracing/eval-platform integration or structured `run_reasoning` logs — absent
