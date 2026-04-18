from __future__ import annotations

import json
from typing import Any, Iterable

from pydantic import BaseModel, ValidationError

from product_matcher_phase2.memory import ProductMemoryItem
from product_matcher_phase2.schemas import (
    CandidateItem,
    CustomerRecord,
    ModelDecision,
    ResultStatus,
    normalize_model_decision_payload,
)


JUDGEMENT_RULES = [
    "必须先理解客户商品的整体业务身份，再判断候选商品是否覆盖同一业务身份。",
    "不要脑补客户没有表达的品牌、规格、单位、包装层级、系列或等级。",
    "不能只按名称相似落码，必须同时检查品名、品牌、规格、单位、包装层级和备注里的身份信号。",
    "规格、单位、包装层级、品牌、系列或等级存在冲突时，不能强自动落码。",
    "证据不够唯一时输出人工审核，允许给出建议候选，但不能自动落码。",
    "记忆只能作为证据参考，不能覆盖当前客户行和候选商品的直接证据。",
    "risk_flags 只能输出下列 RiskFlag 枚举值：core_name_uncertain, brand_conflict, spec_conflict, package_conflict, unit_conflict, series_or_grade_conflict, remark_changes_identity, needs_unstated_assumption, multiple_valid_candidates, insufficient_customer_info, candidate_pool_missing_evidence。",
]

ALLOWED_RISK_FLAGS = [
    "core_name_uncertain",
    "brand_conflict",
    "spec_conflict",
    "package_conflict",
    "unit_conflict",
    "series_or_grade_conflict",
    "remark_changes_identity",
    "needs_unstated_assumption",
    "multiple_valid_candidates",
    "insufficient_customer_info",
    "candidate_pool_missing_evidence",
]

REQUIRED_OUTPUT_FORMAT = {
    "customer_semantic_summary": "string",
    "key_identity_signals": ["string"],
    "strong_constraints": ["string"],
    "weak_constraints": ["string"],
    "ignored_or_noise_signals": ["string"],
    "missing_or_uncertain_signals": ["string"],
    "candidate_assessments": [
        {
            "candidate_id": "string",
            "same_business_identity": "boolean",
            "matched_evidence": ["string"],
            "conflicts": ["string"],
            "missing_evidence": ["string"],
            "risk_flags": list(ALLOWED_RISK_FLAGS),
            "summary": "string",
        }
    ],
    "selected_candidate_id": "string | null",
    "result_status": "strong_auto_code | weak_auto_code | suggested_code | manual_review | unmatched | model_error",
    "risk_flags": list(ALLOWED_RISK_FLAGS),
    "evidence_summary": "string",
    "manual_review_reason": "string",
    "can_auto_code": "boolean",
}


def _dump_model(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def build_model_input_payload(
    record: CustomerRecord,
    candidates: Iterable[CandidateItem],
    applicable_memories: Iterable[ProductMemoryItem] | None = None,
) -> dict[str, Any]:
    return {
        "task": "phase2_product_semantic_translation",
        "version": "0.1",
        "customer_record": _dump_model(record),
        "candidate_products": [_dump_model(candidate) for candidate in candidates],
        "applicable_memories": [
            _dump_model(memory) for memory in (applicable_memories or [])
        ],
        "judgement_rules": list(JUDGEMENT_RULES),
        "required_output_format": REQUIRED_OUTPUT_FORMAT,
    }


def render_model_prompt(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return (
        "你是商品编码对照系统二期的语义判断模型。\n"
        "请根据输入证据判断客户商品与候选商品是否为同一业务身份。\n"
        "必须只返回 JSON，不要返回 Markdown，不要返回解释性正文。\n\n"
        "输入证据如下：\n"
        f"{payload_json}"
    )


def _model_error(reason: str, details: str = "") -> ModelDecision:
    return ModelDecision(
        customer_semantic_summary="",
        key_identity_signals=[],
        strong_constraints=[],
        weak_constraints=[],
        ignored_or_noise_signals=[],
        missing_or_uncertain_signals=[],
        candidate_assessments=[],
        selected_candidate_id=None,
        result_status=ResultStatus.MODEL_ERROR,
        risk_flags=[],
        evidence_summary=details[:1000],
        manual_review_reason=reason,
        can_auto_code=False,
    )


def parse_model_decision_response(response_text: str) -> ModelDecision:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        return _model_error("模型返回无法解析为 JSON。", str(exc))

    try:
        return ModelDecision.model_validate(normalize_model_decision_payload(payload))
    except ValidationError as exc:
        return _model_error("模型返回格式或规则校验失败。", str(exc))
