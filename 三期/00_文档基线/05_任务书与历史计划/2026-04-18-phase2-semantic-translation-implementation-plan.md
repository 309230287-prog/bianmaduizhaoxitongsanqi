# Phase 2 Semantic Translation Implementation Plan

> **For agentic workers:** REQUIRED: Use $executing-plans to implement this plan. If subagents are explicitly authorized later, use $subagent-driven-development for independent tasks. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the second-phase product from requirements into a verified, large-model-led semantic translation workflow, starting with validation samples before product code.

**Architecture:** The implementation proceeds in gates. First create a human-labeled validation set, then build a model I/O contract and offline evaluation harness, then design candidate pool generation, then build a minimal local prototype only after model validation passes. The large model is responsible for semantic understanding and judgment; the application is responsible for Excel handling, context construction, persistence, review, export, and traceability.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, openpyxl, SQLite, httpx, Jinja2 or lightweight frontend. Verification begins with offline scripts and sample files before UI productization.

---

## 1. Source Documents

Before implementation, read these files in order:

- `docs/project-memory.md`
- `docs/requirements/商品编码对照系统-需求文档-二期语义翻译-v0.1.md`
- `docs/route-map/商品编码对照系统-二期语义翻译实施路书-v0.1.md`
- `docs/planning/商品编码对照系统-二期技术执行规格-v0.1.md`
- `项目判断准绳-二期语义翻译-v1.md`

Do not use一期 implementation as the product baseline.

Only consider reusing utility code after the validation workflow is proven.

## 2. Target File Structure

Suggested new files for Phase 1 and Phase 2:

- Create: `samples/phase2/golden_samples_v0.1.xlsx`
- Create: `samples/phase2/golden_samples_schema.md`
- Create: `samples/phase2/model_trial_results_v0.1.xlsx`
- Create: `docs/tasks/二期第一阶段-验证样本与模型验证任务书-v0.1.md`
- Create: `src/product_matcher_phase2/__init__.py`
- Create: `src/product_matcher_phase2/schemas.py`
- Create: `src/product_matcher_phase2/model_io.py`
- Create: `src/product_matcher_phase2/candidate_pool.py`
- Create: `src/product_matcher_phase2/evaluation.py`
- Create: `src/product_matcher_phase2/memory.py`
- Create: `scripts/phase2_build_golden_samples.py`
- Create: `scripts/phase2_run_model_trial.py`
- Create: `tests/phase2/test_schemas.py`
- Create: `tests/phase2/test_candidate_pool.py`
- Create: `tests/phase2/test_evaluation.py`
- Create: `tests/phase2/test_memory.py`

The `product_matcher_phase2` package should be separate from一期 code at first.

This prevents old product logic from silently shaping二期.

## 3. Execution Gates

Do not skip gates.

### Gate 1: Golden Sample Gate

Can proceed only when:

- 30 golden samples exist.
- Each sample has a human-confirmed expected result.
- Each sample has key identity signals and strong constraints marked.
- Each sample has expected result status.

### Gate 2: Model Contract Gate

Can proceed only when:

- Model input template exists.
- Model JSON output schema exists.
- Schema validation tests pass.
- 10 sample model outputs are valid JSON.

### Gate 3: Candidate Pool Gate

Can proceed only when:

- Top10 coverage is measured.
- Top20 coverage is measured.
- Missed candidates are recorded with reasons.

### Gate 4: Product Prototype Gate

Can proceed only when:

- Strong auto-code has no obvious error in golden sample testing.
- Manual-review cases are detected.
- Business-readable explanations are generated.

## 4. Chunk 1: Golden Sample Foundation

### Task 1: Define Golden Sample Schema

**Files:**

- Create: `samples/phase2/golden_samples_schema.md`

- [ ] Step 1: Write the sample schema document.

Required columns:

- `sample_id`
- `customer_name`
- `customer_spec`
- `customer_unit`
- `customer_category`
- `customer_remark`
- `customer_other_fields`
- `expected_company_code`
- `expected_company_name`
- `expected_company_spec`
- `expected_company_unit`
- `expected_result_status`
- `human_reason`
- `key_identity_signals`
- `strong_constraints`
- `weak_constraints`
- `noise_or_display_terms`
- `bias_risk`
- `omission_risk`
- `allow_auto_code`
- `manual_review_reason`

- [ ] Step 2: Review schema against二期需求.

Check:

- Does it capture翻译正确?
- Does it capture偏差?
- Does it capture遗漏?
- Does it capture automatic/manual boundary?

- [ ] Step 3: Save schema.

### Task 2: Create 30 Golden Samples

**Files:**

- Create: `samples/phase2/golden_samples_v0.1.xlsx`

- [ ] Step 1: Select 30 records from `客户商品库.xlsx`.

Coverage requirements:

- 5 obvious strong-auto candidates.
- 5 expression-difference candidates.
- 5 spec/package risk candidates.
- 5 brand/series/grade risk candidates.
- 5 remark or hidden-info candidates.
- 5 manual/unmatched/hard candidates.

- [ ] Step 2: Find expected company product for each sample in `我司商品库.xlsx`.

- [ ] Step 3: Fill human reason and expected status.

- [ ] Step 4: Verify every sample has expected result status.

Allowed statuses:

- `strong_auto_code`
- `weak_auto_code`
- `suggested_code`
- `manual_review`
- `unmatched`

### Task 3: Golden Sample Review

**Files:**

- Modify: `samples/phase2/golden_samples_v0.1.xlsx`

- [ ] Step 1: Check every row has enough evidence.

- [ ] Step 2: Mark uncertain rows as `manual_review`, not auto-code.

- [ ] Step 3: Create a short review note at the top or separate sheet.

Expected result:

- Golden sample table can act as the first exam paper for the model.

## 5. Chunk 2: Model I/O Contract

### Task 4: Define Pydantic Schemas

**Files:**

- Create: `src/product_matcher_phase2/schemas.py`
- Test: `tests/phase2/test_schemas.py`

- [ ] Step 1: Write failing tests for valid model decision parsing.

- [ ] Step 2: Define Pydantic models:

Required models:

- `CustomerRecord`
- `CompanyProduct`
- `CandidateItem`
- `CandidateAssessment`
- `ModelDecision`
- `ResultStatus`
- `RiskFlag`

- [ ] Step 3: Run tests and verify they fail before implementation.

- [ ] Step 4: Implement schemas.

- [ ] Step 5: Run tests and verify they pass.

Validation rules:

- `result_status` must be allowed enum.
- `strong_auto_code` must not include hard conflict risk flags.
- `can_auto_code=true` cannot be used with `manual_review` or `unmatched`.

### Task 5: Define Model Input Builder

**Files:**

- Create: `src/product_matcher_phase2/model_io.py`
- Test: `tests/phase2/test_model_io.py`

- [ ] Step 1: Write tests for model input construction.

- [ ] Step 2: Build customer context from mapped fields and raw fields.

- [ ] Step 3: Build candidate context from candidate pool.

- [ ] Step 4: Ensure all original non-empty fields are preserved.

- [ ] Step 5: Ensure prompt includes no-brainstorming rules:

Rules:

- Do not invent missing brand/spec/unit.
- Do not auto-code when package or unit may affect settlement.
- Explain missing or conflicting evidence.
- Output JSON only.

### Task 6: Run 10-Sample Manual Model Trial

**Files:**

- Create: `samples/phase2/model_trial_results_v0.1.xlsx`
- Create: `scripts/phase2_run_model_trial.py`

- [ ] Step 1: Pick 10 samples from golden sample table.

- [ ] Step 2: Build model input for each.

- [ ] Step 3: Call configured large model.

- [ ] Step 4: Save raw output and parsed JSON.

- [ ] Step 5: Compare model result with expected status.

Gate:

- JSON validity must be 100% for 10 samples before expanding.

## 6. Chunk 3: Candidate Pool

### Task 7: Implement Candidate Pool Baseline

**Files:**

- Create: `src/product_matcher_phase2/candidate_pool.py`
- Test: `tests/phase2/test_candidate_pool.py`

- [ ] Step 1: Write tests for simple candidate inclusion.

Examples:

- Customer `海天金标生抽 500ml` should include company products containing `海天`, `金标`, `生抽`, or `500ml`.
- Customer `番茄` should allow synonym candidates like `西红柿` when equivalence exists.

- [ ] Step 2: Implement baseline candidate scoring.

Candidate sources:

- name token
- brand token
- spec token
- unit token
- category
- synonym/equivalence
- history relation

- [ ] Step 3: Return top 10 by default, max 20.

- [ ] Step 4: Preserve candidate source reasons.

### Task 8: Measure Candidate Coverage

**Files:**

- Create: `src/product_matcher_phase2/evaluation.py`
- Test: `tests/phase2/test_evaluation.py`

- [ ] Step 1: Write tests for TopN coverage calculation.

- [ ] Step 2: Implement coverage metrics.

Metrics:

- Top10 coverage
- Top20 coverage
- missed expected products
- missed reason notes

- [ ] Step 3: Run against golden samples.

Gate:

- Top10 target: >= 90%
- Top20 target: >= 95%

If target not met, do not proceed to product prototype.

## 7. Chunk 4: Offline Evaluation Report

### Task 9: Generate Evaluation Report

**Files:**

- Create: `samples/phase2/evaluation_report_v0.1.md`

- [ ] Step 1: Summarize golden sample counts by expected status.

- [ ] Step 2: Summarize candidate pool coverage.

- [ ] Step 3: Summarize model JSON validity.

- [ ] Step 4: Summarize strong-auto errors.

- [ ] Step 5: Summarize manual-review recall.

Go/no-go criteria:

- No obvious wrong `strong_auto_code`.
- JSON validity meets target.
- Candidate coverage meets target.
- Manual-review cases are not forced into auto-code.

## 8. Chunk 5: Product Memory System

### Task 10: Define Product Memory Models

**Files:**

- Create: `src/product_matcher_phase2/memory.py`
- Test: `tests/phase2/test_memory.py`

- [ ] Step 1: Write failing tests for memory item validation.

Memory types:

- manual confirmation memory
- customer expression pattern memory
- product semantic memory
- business equivalence memory
- failure case memory

- [ ] Step 2: Implement memory data models.

- [ ] Step 3: Implement applicability checks.

Rules:

- A memory item must have a source.
- Weak-auto-supporting memory must be human-confirmed.
- Memory cannot apply when key brand/spec/unit/package conditions conflict.
- Failure memory should block strong auto-code when matching risk appears.

- [ ] Step 4: Run tests and verify they pass.

### Task 11: Define Memory Retrieval Flow

**Files:**

- Modify: `src/product_matcher_phase2/memory.py`
- Test: `tests/phase2/test_memory.py`

- [ ] Step 1: Write tests for retrieving relevant memory by customer record.

- [ ] Step 2: Implement retrieval for:

Retrieval categories:

- manual confirmations
- customer expression patterns
- product semantic terms
- business equivalences
- failure cases

- [ ] Step 3: Ensure memory output can be inserted into model prompt context.

- [ ] Step 4: Ensure memory usage is logged.

Gate:

- Memory can assist candidate pool and model prompt.
- Memory cannot silently override current evidence.

## 9. Chunk 6: Minimal Prototype Readiness

### Task 12: Decide Prototype Scope

**Files:**

- Create: `docs/tasks/二期最小产品原型范围-v0.1.md`

- [ ] Step 1: List what the prototype must include.

Must include:

- import customer workbook
- import company workbook
- select records
- build candidate pool
- call model
- show evidence alignment
- show risk flags
- human review action
- product memory hit display
- export results

- [ ] Step 2: List what the prototype must not include.

Must not include:

- full permission system
- multi-user workflow
- cloud deployment
- complex dashboard
- automatic mass production without validation

- [ ] Step 3: Review with business user before coding.

## 9. Verification Commands

Commands will be finalized when code exists.

Initial expected commands:

```powershell
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python -m unittest discover -s tests -v
```

If pytest is introduced:

```powershell
python -m pytest tests/phase2 -v
```

## 10. Implementation Discipline

- No production code before a failing test.
- No product prototype before sample validation.
- No automatic coding result without evidence output.
- No reuse of一期 product logic as二期 baseline.
- Every model call must be traceable.
- Every model output must be schema-validated.
- Every manual override must be recorded.

## 11. Handoff

The first implementation task is:

**Create `samples/phase2/golden_samples_schema.md` and `samples/phase2/golden_samples_v0.1.xlsx`.**

Do not begin model integration until the 30-sample golden set exists.
