# Phase 2 Judgement Chain Debug Plan

> **For agentic workers:** REQUIRED: Use $executing-plans to implement this plan. In low-token mode, do not spawn subagents unless the user explicitly re-enables them. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current Phase 2 prototype from "framework exists" into "the 10 golden trial samples can be judged with clear, measurable business logic."

**Architecture:** Treat the product as a judgement chain, not as a UI-first app. The chain is: golden sample -> candidate evidence -> model prompt -> model JSON -> parser/schema -> evaluator -> diagnosis -> product display. We only move to productization after this chain produces acceptable evidence on the 10-sample trial set.

**Tech Stack:** Python, Pydantic, openpyxl, FastAPI/Jinja for display, pytest for verification, local Markdown diagnostics.

---

## 1. Why The Work Felt Messy

The last round mixed three different layers:

- product shell work: page, job, download, summary card
- guardrail work: schema, diagnostics, unsafe auto-code counters
- judgement-chain work: candidate evidence, prompt, model output, result status

Those layers are related, but they should not be worked randomly.

The current blocker is not the page. The blocker is the judgement chain.

## 2. Current Facts

Current verified state:

- Test suite: `91 passed, 2 warnings`
- Phase 2 workbench exists.
- DeepSeek-compatible model calling exists.
- Trial result xlsx can be generated.
- Diagnostic Markdown can be generated.
- Homepage can display diagnostic red lines.

Current trial problem:

- The original xlsx stored many rows as `model_error`.
- Current parser can now parse most raw JSON after risk flag normalization.
- Re-reading raw outputs with the current parser suggests the model is not completely failing.
- However, selected-code accuracy is still poor.

Observed likely causes:

- Candidate evidence is not structured enough.
- Company product `spec` is often missing, while specs are embedded inside product names.
- Prompt rules are too conservative around "multiple similar candidates".
- Result status boundaries are not explicit enough.
- Schema does not yet enforce every cross-field invariant the model should obey.
- Diagnostics still need to distinguish old recorded parse state from current parser state.

## 3. New Execution Order

Do not continue by adding more UI first.

Use this order:

1. Fix measurement.
2. Fix status definitions.
3. Fix candidate evidence.
4. Fix prompt contract.
5. Re-run 10 samples.
6. Only then decide whether product 1.0 is close.

## 4. Acceptance Targets For The 10-Sample Trial

Minimum to continue:

- JSON/current parser valid count: 10/10
- dangerous auto-code count: 0
- strong-auto obvious errors: 0
- candidate-empty cases classified as `unmatched`, not generic `manual_review`
- every non-auto result has a business-readable reason

Target before productizing:

- status match count: at least 8/10
- selected code match count: at least 7/10 among rows with expected company code
- selected code mismatch count: no unexplained mismatch
- any mismatch must have a categorized root cause

Hard stop:

- Any `unsafe_auto_code_count > 0` after prompt/schema/candidate fixes means no automatic coding productization.

## 5. Task 1: Make Diagnostics Recompute With Current Parser

**Files:**

- Modify: `src/product_matcher_phase2/trial_diagnostics.py`
- Modify: `tests/phase2/test_trial_diagnostics.py`
- Regenerate: `samples/phase2/model_trial_diagnostics_deepseek_v0.1.md`

- [ ] Step 1: Write a failing test proving diagnostics can recompute parsed status from `raw_model_output`.
- [ ] Step 2: Add diagnostic fields:
  - `current_parser_valid_count`
  - `current_status_match_count`
  - `current_selected_code_match_count`
  - `current_selected_code_mismatch_count`
  - `current_unsafe_auto_code_count`
- [ ] Step 3: Preserve old recorded fields separately, so old xlsx columns do not hide current parser behavior.
- [ ] Step 4: Run `python -m pytest tests/phase2/test_trial_diagnostics.py -q`.
- [ ] Step 5: Regenerate diagnostics:
  - `python scripts/phase2_diagnose_model_trial.py`
- [ ] Step 6: Commit:
  - `git commit -m "fix: recompute phase2 diagnostics with current parser"`

## 6. Task 2: Lock Result Status Definitions

**Files:**

- Modify: `src/product_matcher_phase2/model_io.py`
- Modify: `tests/phase2/test_model_io.py`
- Modify: `src/product_matcher_phase2/schemas.py`
- Modify: `tests/phase2/test_schemas.py`

- [ ] Step 1: Add prompt rules for exact status boundaries:
  - `strong_auto_code`: one selected candidate, all hard identity signals match, no hard conflict, `can_auto_code=true`
  - `weak_auto_code`: selected candidate exists, business equivalence is supported, no hard conflict, `can_auto_code=true`
  - `suggested_code`: selected candidate exists, useful suggestion, but not enough evidence for auto-code, `can_auto_code=false`
  - `manual_review`: candidates exist but evidence is not unique or conflict must be reviewed, `can_auto_code=false`
  - `unmatched`: no candidate can explain the customer record or candidate pool is empty, `can_auto_code=false`
- [ ] Step 2: Add schema invariant tests:
  - `strong_auto_code` requires `can_auto_code=true`
  - `unmatched` requires no selected candidate
  - `suggested_code` can have selected candidate but cannot auto-code
- [ ] Step 3: Implement minimal schema validators.
- [ ] Step 4: Run:
  - `python -m pytest tests/phase2/test_model_io.py tests/phase2/test_schemas.py -q`
- [ ] Step 5: Commit:
  - `git commit -m "fix: lock phase2 result status contract"`

## 7. Task 3: Structure Candidate Evidence Before Prompting

**Files:**

- Modify: `src/product_matcher_phase2/candidate_generation.py`
- Modify: `tests/phase2/test_candidate_generation.py`
- Modify: `src/product_matcher_phase2/model_io.py`
- Modify: `tests/phase2/test_model_io.py`

- [ ] Step 1: Add tests for extracting evidence from company product names:
  - visible spec tokens such as `1*6*1.9L`, `500ml`, `12*410ml`
  - inferred package hints such as `件`, `瓶`, `罐`
  - name terms such as brand/product/series words
- [ ] Step 2: Add candidate evidence fields to model payload without changing raw product data:
  - `candidate_evidence.name_terms`
  - `candidate_evidence.spec_tokens`
  - `candidate_evidence.unit`
  - `candidate_evidence.match_sources`
  - `candidate_evidence.conflict_notes`
- [ ] Step 3: Make prompt tell the model to judge from `candidate_evidence` first, raw name second.
- [ ] Step 4: Run:
  - `python -m pytest tests/phase2/test_candidate_generation.py tests/phase2/test_model_io.py -q`
- [ ] Step 5: Commit:
  - `git commit -m "feat: add structured phase2 candidate evidence"`

## 8. Task 4: Re-run Only The 10-Sample Trial

**Files:**

- Regenerate: `samples/phase2/model_trial_results_deepseek_v0.1.xlsx`
- Regenerate: `samples/phase2/model_trial_diagnostics_deepseek_v0.1.md`
- Update: `omc/state/current/2026-04-18-phase2-agent-orchestration/progress-2026-04-19.md`

- [ ] Step 1: Confirm model settings are using the intended DeepSeek-compatible config.
- [ ] Step 2: Run only 10 samples, not the full customer library.
- [ ] Step 3: Regenerate diagnostics.
- [ ] Step 4: Compare against acceptance targets in this plan.
- [ ] Step 5: If `unsafe_auto_code_count > 0`, stop productization and analyze that row first.
- [ ] Step 6: Commit trial artifacts and progress notes only if they reflect the actual result.

## 9. What Not To Do Next

- Do not add more product UI before judgement-chain metrics improve.
- Do not run the full customer library yet.
- Do not call the result "1.0 usable" while the 10-sample trial misses the acceptance targets.
- Do not hide model failures by weakening tests.
- Do not open more agents unless the user explicitly re-enables multi-agent mode.

## 10. Plain-Language Summary

The next goal is not "make the screen nicer".

The next goal is:

> make the system judge 10 known examples in a way that matches our business understanding.

If that works, productization becomes meaningful.

If that does not work, more UI will only make a wrong judgement engine look polished.
