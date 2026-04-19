from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from openpyxl import Workbook

from product_matcher_phase2.model_io import parse_model_decision_response
from product_matcher_phase2.schemas import ModelDecision, ResultStatus


ModelCaller = Callable[[dict[str, Any]], dict[str, Any] | str]


@dataclass(frozen=True)
class ModelTrialCase:
    sample_id: str
    sample_group: str
    expected_company_code: str
    expected_result_status: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ModelTrialResult:
    sample_id: str
    sample_group: str
    expected_company_code: str
    expected_result_status: str
    raw_model_output: str
    parse_ok: bool
    parsed_result_status: str
    status_matches_expected: bool
    selected_candidate_id: str
    selected_company_code: str
    selected_code_matches_expected: bool
    can_auto_code: bool
    evidence_summary: str
    manual_review_reason: str
    error_message: str


def load_trial_cases_jsonl(path: str | Path) -> list[ModelTrialCase]:
    cases: list[ModelTrialCase] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cases.append(
            ModelTrialCase(
                sample_id=str(row.get("sample_id", "")),
                sample_group=str(row.get("sample_group", "")),
                expected_company_code=str(row.get("expected_company_code", "")),
                expected_result_status=str(row.get("expected_result_status", "")),
                payload=row.get("payload") or {},
            )
        )
    return cases


def run_trial_cases(
    cases: Iterable[ModelTrialCase],
    call_model: ModelCaller,
) -> list[ModelTrialResult]:
    return [_run_one_case(case, call_model) for case in cases]


def _run_one_case(case: ModelTrialCase, call_model: ModelCaller) -> ModelTrialResult:
    try:
        model_output = call_model(case.payload)
        raw_output = _serialize_model_output(model_output)
        decision = parse_model_decision_response(raw_output)
        parse_ok = decision.result_status != ResultStatus.MODEL_ERROR
        error_message = ""
    except Exception as exc:
        raw_output = ""
        decision = _call_error_decision(str(exc))
        parse_ok = False
        error_message = str(exc)

    selected_company_code = _selected_company_code(case.payload, decision.selected_candidate_id)
    selected_code_matches_expected = bool(case.expected_company_code) and (
        selected_company_code == case.expected_company_code
    )
    return ModelTrialResult(
        sample_id=case.sample_id,
        sample_group=case.sample_group,
        expected_company_code=case.expected_company_code,
        expected_result_status=case.expected_result_status,
        raw_model_output=raw_output,
        parse_ok=parse_ok,
        parsed_result_status=decision.result_status.value,
        status_matches_expected=decision.result_status.value == case.expected_result_status,
        selected_candidate_id=decision.selected_candidate_id or "",
        selected_company_code=selected_company_code,
        selected_code_matches_expected=selected_code_matches_expected,
        can_auto_code=decision.can_auto_code,
        evidence_summary=decision.evidence_summary,
        manual_review_reason=decision.manual_review_reason,
        error_message=error_message,
    )


def _serialize_model_output(model_output: dict[str, Any] | str) -> str:
    if isinstance(model_output, str):
        return model_output
    return json.dumps(model_output, ensure_ascii=False, sort_keys=True)


def _call_error_decision(message: str) -> ModelDecision:
    return ModelDecision(
        customer_semantic_summary="",
        selected_candidate_id=None,
        result_status=ResultStatus.MODEL_ERROR,
        evidence_summary="",
        manual_review_reason=f"模型调用失败：{message}",
        can_auto_code=False,
    )


def _selected_company_code(payload: dict[str, Any], selected_candidate_id: str | None) -> str:
    if not selected_candidate_id:
        return ""
    for candidate in payload.get("candidate_products", []):
        if candidate.get("candidate_id") != selected_candidate_id:
            continue
        product = candidate.get("product") or {}
        return str(product.get("code", ""))
    return ""


TRIAL_RESULT_HEADERS = [
    "sample_id",
    "sample_group",
    "expected_company_code",
    "expected_result_status",
    "parsed_result_status",
    "status_matches_expected",
    "parse_ok",
    "selected_candidate_id",
    "selected_company_code",
    "selected_code_matches_expected",
    "can_auto_code",
    "evidence_summary",
    "manual_review_reason",
    "error_message",
    "raw_model_output",
]


def write_trial_results_xlsx(results: Iterable[ModelTrialResult], path: str | Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "model_trial_results"
    worksheet.append(TRIAL_RESULT_HEADERS)
    for result in results:
        worksheet.append([getattr(result, header) for header in TRIAL_RESULT_HEADERS])

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    workbook.close()


def summarize_trial_results(results: Iterable[ModelTrialResult]) -> dict[str, Any]:
    result_list = list(results)
    total_count = len(result_list)
    json_valid_count = sum(1 for result in result_list if result.parse_ok)
    status_match_count = sum(1 for result in result_list if result.status_matches_expected)
    code_evaluated_results = [result for result in result_list if result.expected_company_code]
    selected_code_match_count = sum(
        1 for result in code_evaluated_results if result.selected_code_matches_expected
    )
    selected_code_mismatch_count = len(code_evaluated_results) - selected_code_match_count
    auto_code_count = sum(1 for result in result_list if result.can_auto_code)
    return {
        "total_count": total_count,
        "json_valid_count": json_valid_count,
        "json_valid_rate": json_valid_count / total_count if total_count else 0.0,
        "status_match_count": status_match_count,
        "status_match_rate": status_match_count / total_count if total_count else 0.0,
        "selected_code_match_count": selected_code_match_count,
        "selected_code_mismatch_count": selected_code_mismatch_count,
        "auto_code_count": auto_code_count,
    }
