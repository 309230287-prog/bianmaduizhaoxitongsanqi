from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from openpyxl import Workbook

from product_matcher_phase2.candidate_generation import extract_spec_tokens
from product_matcher_phase2.model_io import parse_model_decision_response
from product_matcher_phase2.schemas import ModelDecision, ResultStatus, RiskFlag


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
    *,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[ModelTrialResult]:
    case_list = list(cases)
    results = []
    total = len(case_list)
    for index, case in enumerate(case_list, start=1):
        results.append(_run_one_case(case, call_model))
        if on_progress:
            on_progress(index, total)
    return results


def _run_one_case(case: ModelTrialCase, call_model: ModelCaller) -> ModelTrialResult:
    try:
        model_output = call_model(case.payload)
        raw_output = _serialize_model_output(model_output)
        decision = parse_model_decision_response(raw_output)
        decision = apply_payload_safety_gate(case.payload, decision)
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


def apply_payload_safety_gate(payload: dict[str, Any], decision: ModelDecision) -> ModelDecision:
    if (
        not decision.can_auto_code
        and not decision.selected_candidate_id
        and decision.result_status
        in {ResultStatus.SUGGESTED_CODE, ResultStatus.MANUAL_REVIEW}
    ):
        decision = _add_top_candidate_suggestion(payload, decision)

    if not decision.can_auto_code and decision.result_status == ResultStatus.MANUAL_REVIEW:
        decision = _promote_manual_to_suggested_when_top_candidate_is_useful(payload, decision)

    if not decision.can_auto_code or not decision.selected_candidate_id:
        return decision

    customer_record = payload.get("customer_record") or {}
    mapped_fields = customer_record.get("mapped_fields") if isinstance(customer_record, dict) else {}
    customer_spec = str((mapped_fields or {}).get("spec", "")).strip() if isinstance(mapped_fields, dict) else ""
    customer_unit = str((mapped_fields or {}).get("unit", "")).strip() if isinstance(mapped_fields, dict) else ""
    customer_spec_tokens = extract_spec_tokens(customer_spec)
    selected_candidate = _selected_candidate_payload(payload, decision.selected_candidate_id)
    candidate_evidence = selected_candidate.get("candidate_evidence") if selected_candidate else {}

    candidate_unit = _candidate_unit(selected_candidate, candidate_evidence)
    if customer_unit and candidate_unit and customer_unit != candidate_unit:
        return _downgrade_auto_decision(
            decision,
            status=ResultStatus.MANUAL_REVIEW,
            risk=RiskFlag.UNIT_CONFLICT,
            reason=f"安全闸拦截：单位冲突，客户单位={customer_unit}，候选单位={candidate_unit}，不能自动落码。",
        )

    if not customer_spec_tokens:
        return decision

    candidate_spec_tokens = set(candidate_evidence.get("spec_tokens") or []) if isinstance(candidate_evidence, dict) else set()
    if not _spec_tokens_match(customer_spec_tokens, candidate_spec_tokens):
        status = ResultStatus.SUGGESTED_CODE if not candidate_spec_tokens else ResultStatus.MANUAL_REVIEW
        reason = (
            "安全闸拦截：客户有明确规格，但选中候选缺少与客户规格匹配的证据，不能自动落码。"
            if not candidate_spec_tokens
            else "安全闸拦截：规格或包装层级不一致，不能自动落码。"
        )
        return _downgrade_auto_decision(decision, status=status, risk=RiskFlag.SPEC_CONFLICT, reason=reason)

    require_spec_in_name = _candidate_match_sources(candidate_evidence).issuperset({"spec_in_product_name"})
    duplicate_count = sum(
        1
        for candidate in payload.get("candidate_products", [])
        if _candidate_has_same_identity_evidence(
            candidate,
            customer_unit,
            customer_spec_tokens,
            require_spec_in_name=require_spec_in_name,
        )
    )
    if duplicate_count > 1:
        return _downgrade_auto_decision(
            decision,
            status=ResultStatus.MANUAL_REVIEW,
            risk=RiskFlag.MULTIPLE_VALID_CANDIDATES,
            reason="安全闸拦截：多个候选都具备同一商品身份证据，不能自动落码。",
        )

    if decision.result_status == ResultStatus.STRONG_AUTO_CODE and _has_display_wrapped_spec(customer_spec):
        return _change_auto_status(
            decision,
            ResultStatus.WEAK_AUTO_CODE,
            "安全闸调整：客户规格存在括号等展示加工痕迹，候选完整匹配，降为弱自动落码。",
        )

    return decision


def _downgrade_auto_decision(
    decision: ModelDecision,
    *,
    status: ResultStatus,
    risk: RiskFlag,
    reason: str,
) -> ModelDecision:
    downgraded = decision.model_dump(mode="json")
    downgraded["result_status"] = status.value
    downgraded["can_auto_code"] = False
    risk_flags = list(dict.fromkeys([*downgraded.get("risk_flags", []), risk.value]))
    downgraded["risk_flags"] = risk_flags
    downgraded["manual_review_reason"] = reason
    downgraded["evidence_summary"] = "；".join(
        part for part in [str(downgraded.get("evidence_summary", "")).strip(), reason] if part
    )
    return ModelDecision.model_validate(downgraded)


def _add_top_candidate_suggestion(payload: dict[str, Any], decision: ModelDecision) -> ModelDecision:
    candidates = payload.get("candidate_products") or []
    if not candidates:
        return decision

    first_candidate = candidates[0]
    candidate_id = str(first_candidate.get("candidate_id", "")).strip()
    if not candidate_id:
        return decision

    updated = decision.model_dump(mode="json")
    updated["selected_candidate_id"] = candidate_id
    note = f"系统补充建议候选：{candidate_id}，仅供人工审核参考，不自动落码。"
    updated["evidence_summary"] = "；".join(
        part for part in [str(updated.get("evidence_summary", "")).strip(), note] if part
    )
    return ModelDecision.model_validate(updated)


def _promote_manual_to_suggested_when_top_candidate_is_useful(
    payload: dict[str, Any],
    decision: ModelDecision,
) -> ModelDecision:
    if not decision.selected_candidate_id:
        return decision
    candidates = payload.get("candidate_products") or []
    if not candidates or candidates[0].get("candidate_id") != decision.selected_candidate_id:
        return decision
    first_candidate = candidates[0]
    evidence = first_candidate.get("candidate_evidence") or {}
    if not isinstance(evidence, dict):
        return decision
    if evidence.get("conflict_notes"):
        return decision
    match_sources = _candidate_match_sources(evidence)
    if "unit_match" not in match_sources:
        return decision
    customer_record = payload.get("customer_record") or {}
    mapped_fields = customer_record.get("mapped_fields") if isinstance(customer_record, dict) else {}
    customer_text = " ".join(str(value) for value in (mapped_fields or {}).values()) if isinstance(mapped_fields, dict) else ""
    customer_tokens = extract_spec_tokens(customer_text)
    candidate_tokens = set(evidence.get("spec_tokens") or [])
    if customer_tokens and not _spec_tokens_match(customer_tokens, candidate_tokens):
        return decision
    if _top_two_are_duplicate_full_matches(candidates):
        return decision

    updated = decision.model_dump(mode="json")
    updated["result_status"] = ResultStatus.SUGGESTED_CODE.value
    note = "系统调整：首候选具备名称/规格/单位方向性证据，但仍需人工确认，改为建议编码。"
    updated["evidence_summary"] = "；".join(
        part for part in [str(updated.get("evidence_summary", "")).strip(), note] if part
    )
    return ModelDecision.model_validate(updated)


def _change_auto_status(decision: ModelDecision, status: ResultStatus, reason: str) -> ModelDecision:
    updated = decision.model_dump(mode="json")
    updated["result_status"] = status.value
    updated["evidence_summary"] = "；".join(
        part for part in [str(updated.get("evidence_summary", "")).strip(), reason] if part
    )
    return ModelDecision.model_validate(updated)


def _spec_tokens_match(customer_tokens: set[str], candidate_tokens: set[str]) -> bool:
    if not customer_tokens:
        return True
    composite_tokens = {token for token in customer_tokens if "*" in token}
    if composite_tokens:
        return bool(composite_tokens.intersection(candidate_tokens))
    return bool(customer_tokens.intersection(candidate_tokens))


def _candidate_unit(candidate: dict[str, Any], candidate_evidence: object) -> str:
    if isinstance(candidate_evidence, dict) and candidate_evidence.get("unit"):
        return str(candidate_evidence.get("unit", "")).strip()
    product = candidate.get("product") if isinstance(candidate, dict) else {}
    return str((product or {}).get("unit", "")).strip() if isinstance(product, dict) else ""


def _candidate_has_same_identity_evidence(
    candidate: dict[str, Any],
    customer_unit: str,
    customer_spec_tokens: set[str],
    *,
    require_spec_in_name: bool = False,
) -> bool:
    evidence = candidate.get("candidate_evidence") if isinstance(candidate, dict) else {}
    if not isinstance(evidence, dict):
        return False
    match_sources = _candidate_match_sources(evidence)
    if not match_sources.intersection({"name_exact", "name_contains", "name_terms_match"}):
        return False
    if require_spec_in_name and "spec_in_product_name" not in match_sources:
        return False
    if customer_unit and _candidate_unit(candidate, evidence) != customer_unit:
        return False
    candidate_spec_tokens = set(evidence.get("spec_tokens") or [])
    if customer_spec_tokens and not _spec_tokens_match(customer_spec_tokens, candidate_spec_tokens):
        return False
    conflict_notes = [str(note) for note in evidence.get("conflict_notes") or []]
    return not conflict_notes


def _candidate_match_sources(candidate_evidence: object) -> set[str]:
    if not isinstance(candidate_evidence, dict):
        return set()
    return {str(source) for source in candidate_evidence.get("match_sources") or []}


def _top_two_are_duplicate_full_matches(candidates: list[dict[str, Any]]) -> bool:
    if len(candidates) < 2:
        return False
    first = candidates[0].get("candidate_evidence") or {}
    second = candidates[1].get("candidate_evidence") or {}
    if not isinstance(first, dict) or not isinstance(second, dict):
        return False
    if first.get("conflict_notes") or second.get("conflict_notes"):
        return False
    first_sources = _candidate_match_sources(first)
    second_sources = _candidate_match_sources(second)
    required = {"spec_in_product_name", "unit_match"}
    return required.issubset(first_sources) and required.issubset(second_sources)


def _has_display_wrapped_spec(spec: str) -> bool:
    stripped = spec.strip()
    return (stripped.startswith("[") and stripped.endswith("]")) or (
        stripped.startswith("【") and stripped.endswith("】")
    )


def _selected_candidate_payload(payload: dict[str, Any], selected_candidate_id: str) -> dict[str, Any]:
    for candidate in payload.get("candidate_products", []):
        if candidate.get("candidate_id") == selected_candidate_id:
            return candidate
    return {}


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
    unsafe_auto_code_count = sum(1 for result in result_list if _is_unsafe_auto_code(result))
    return {
        "total_count": total_count,
        "json_valid_count": json_valid_count,
        "json_valid_rate": json_valid_count / total_count if total_count else 0.0,
        "status_match_count": status_match_count,
        "status_match_rate": status_match_count / total_count if total_count else 0.0,
        "selected_code_match_count": selected_code_match_count,
        "selected_code_mismatch_count": selected_code_mismatch_count,
        "auto_code_count": auto_code_count,
        "unsafe_auto_code_count": unsafe_auto_code_count,
    }


def _is_unsafe_auto_code(result: ModelTrialResult) -> bool:
    if not result.can_auto_code:
        return False
    if result.expected_result_status not in {
        ResultStatus.STRONG_AUTO_CODE.value,
        ResultStatus.WEAK_AUTO_CODE.value,
    }:
        return True
    if result.expected_company_code and not result.selected_code_matches_expected:
        return True
    return False
