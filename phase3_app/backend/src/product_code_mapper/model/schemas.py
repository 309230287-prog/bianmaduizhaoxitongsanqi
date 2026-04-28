"""Model output JSON schemas, parsing, and validation.

All model outputs must pass structural validation before the system acts on them.
If validation fails, the result enters manual review — the system never silently
accepts malformed model output.
"""

from dataclasses import dataclass, field
from typing import Any

from product_code_mapper.domain.statuses import MatchStatus

VALID_STATUS_VALUES = frozenset(
    [
        MatchStatus.AUTO_CODE.value,
        MatchStatus.AUTO_CODE_WITH_DIFFERENCE.value,
        MatchStatus.SUGGESTED_REVIEW.value,
        MatchStatus.MANUAL_REVIEW.value,
        MatchStatus.NO_RELIABLE_MATCH.value,
    ]
)

REQUIRED_COMPARE_FIELDS = [
    "selected_candidate_index",
    "status",
    "reason_summary",
    "evidence_summary",
    "risk_summary",
    "matched_signals",
    "unmatched_signals",
    "conflict_signals",
    "need_manual_review",
]


@dataclass(frozen=True)
class CompareResult:
    """Parsed and validated model comparison output."""

    selected_candidate_index: int
    status: str
    reason_summary: str
    evidence_summary: str
    risk_summary: str
    matched_signals: list[str] = field(default_factory=list)
    unmatched_signals: list[str] = field(default_factory=list)
    conflict_signals: list[str] = field(default_factory=list)
    need_manual_review: bool = False


class ModelOutputValidationError(ValueError):
    pass


def validate_compare_payload(payload: dict[str, Any]) -> CompareResult:
    """Parse and validate a model compare output payload.

    Returns a CompareResult if valid.
    Raises ModelOutputValidationError if the output is structurally invalid.
    """
    if not isinstance(payload, dict):
        raise ModelOutputValidationError("模型输出不是 JSON 对象")

    missing = [field for field in REQUIRED_COMPARE_FIELDS if field not in payload]
    if missing:
        raise ModelOutputValidationError(f"模型输出缺少必要字段: {', '.join(missing)}")

    status = str(payload["status"]).strip()
    if status not in VALID_STATUS_VALUES:
        raise ModelOutputValidationError(f"模型输出的状态值不合法: {status}")

    index = payload.get("selected_candidate_index", -1)
    try:
        index = int(index)
    except (ValueError, TypeError):
        index = -1

    reason = str(payload.get("reason_summary", "")).strip()
    if not reason:
        raise ModelOutputValidationError("模型输出缺少推荐理由")

    evidence = str(payload.get("evidence_summary", "")).strip()
    risk = str(payload.get("risk_summary", "")).strip()
    matched = _as_str_list(payload.get("matched_signals", []))
    unmatched = _as_str_list(payload.get("unmatched_signals", []))
    conflict = _as_str_list(payload.get("conflict_signals", []))
    need_manual = bool(payload.get("need_manual_review", False))

    # Safety rule: if status says manual review, must enforce it
    if status in {MatchStatus.MANUAL_REVIEW.value, MatchStatus.NO_RELIABLE_MATCH.value}:
        need_manual = True

    # Safety rule: must have either matched signals or conflict signals
    if not matched and not conflict:
        risk = (risk + " 注意：模型未明确列出匹配或冲突信号。").strip()

    return CompareResult(
        selected_candidate_index=index,
        status=status,
        reason_summary=reason,
        evidence_summary=evidence,
        risk_summary=risk,
        matched_signals=matched,
        unmatched_signals=unmatched,
        conflict_signals=conflict,
        need_manual_review=need_manual,
    )


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]
