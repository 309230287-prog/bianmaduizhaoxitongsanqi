from __future__ import annotations

from contextvars import ContextVar
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ResultStatus(str, Enum):
    STRONG_AUTO_CODE = "strong_auto_code"
    WEAK_AUTO_CODE = "weak_auto_code"
    SUGGESTED_CODE = "suggested_code"
    MANUAL_REVIEW = "manual_review"
    UNMATCHED = "unmatched"
    MODEL_ERROR = "model_error"


class RiskFlag(str, Enum):
    CORE_NAME_UNCERTAIN = "core_name_uncertain"
    BRAND_CONFLICT = "brand_conflict"
    SPEC_CONFLICT = "spec_conflict"
    PACKAGE_CONFLICT = "package_conflict"
    UNIT_CONFLICT = "unit_conflict"
    SERIES_OR_GRADE_CONFLICT = "series_or_grade_conflict"
    REMARK_CHANGES_IDENTITY = "remark_changes_identity"
    NEEDS_UNSTATED_ASSUMPTION = "needs_unstated_assumption"
    MULTIPLE_VALID_CANDIDATES = "multiple_valid_candidates"
    INSUFFICIENT_CUSTOMER_INFO = "insufficient_customer_info"
    CANDIDATE_POOL_MISSING_EVIDENCE = "candidate_pool_missing_evidence"


_NORMALIZE_RISK_FLAGS = ContextVar("phase2_normalize_risk_flags", default=True)


RISK_FLAG_ALIASES: dict[str, RiskFlag] = {
    "brand_mismatch": RiskFlag.BRAND_CONFLICT,
    "品牌冲突": RiskFlag.BRAND_CONFLICT,
    "spec_mismatch": RiskFlag.SPEC_CONFLICT,
    "spec_missing": RiskFlag.INSUFFICIENT_CUSTOMER_INFO,
    "规格冲突": RiskFlag.SPEC_CONFLICT,
    "package_mismatch": RiskFlag.PACKAGE_CONFLICT,
    "包装冲突": RiskFlag.PACKAGE_CONFLICT,
    "unit_mismatch": RiskFlag.UNIT_CONFLICT,
    "单位冲突": RiskFlag.UNIT_CONFLICT,
    "multiple_candidates": RiskFlag.MULTIPLE_VALID_CANDIDATES,
    "多个候选": RiskFlag.MULTIPLE_VALID_CANDIDATES,
    "多个候选匹配": RiskFlag.MULTIPLE_VALID_CANDIDATES,
    "insufficient_info": RiskFlag.INSUFFICIENT_CUSTOMER_INFO,
    "信息不足": RiskFlag.INSUFFICIENT_CUSTOMER_INFO,
    "name_partial_match": RiskFlag.CORE_NAME_UNCERTAIN,
    "名称冲突": RiskFlag.CORE_NAME_UNCERTAIN,
    "分类冲突": RiskFlag.CORE_NAME_UNCERTAIN,
}


def _normalize_risk_flag_value(value: object) -> object:
    if isinstance(value, RiskFlag):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned in RISK_FLAG_ALIASES:
            return RISK_FLAG_ALIASES[cleaned]
        try:
            return RiskFlag(cleaned)
        except ValueError:
            inferred = _infer_risk_flag_from_text(cleaned)
            return inferred if inferred is not None else value
    return value


def _infer_risk_flag_from_text(text: str) -> RiskFlag | None:
    if not text:
        return None
    lowered = text.lower()
    if "multiple candidates" in lowered:
        return RiskFlag.MULTIPLE_VALID_CANDIDATES
    if "unit" in lowered and ("conflict" in lowered or "mismatch" in lowered):
        return RiskFlag.UNIT_CONFLICT
    if "spec" in lowered and ("conflict" in lowered or "mismatch" in lowered or "missing" in lowered):
        return RiskFlag.SPEC_CONFLICT
    if "候选商品列表为空" in text or "候选池为空" in text or "无候选商品" in text:
        return RiskFlag.CANDIDATE_POOL_MISSING_EVIDENCE
    if "多个候选" in text or "其他候选" in text or "混淆" in text:
        return RiskFlag.MULTIPLE_VALID_CANDIDATES
    if "未表达" in text or "脑补" in text:
        return RiskFlag.NEEDS_UNSTATED_ASSUMPTION
    if "备注" in text:
        return RiskFlag.REMARK_CHANGES_IDENTITY
    if "系列" in text or "等级" in text:
        return RiskFlag.SERIES_OR_GRADE_CONFLICT
    if "包装" in text or "包装层级" in text:
        return RiskFlag.PACKAGE_CONFLICT
    if "单位" in text:
        return RiskFlag.UNIT_CONFLICT
    if "规格缺失" in text or "规格信息不完整" in text:
        return RiskFlag.INSUFFICIENT_CUSTOMER_INFO
    if "规格" in text:
        return RiskFlag.SPEC_CONFLICT
    if "品牌" in text:
        return RiskFlag.BRAND_CONFLICT
    if "品名" in text or "分类" in text:
        return RiskFlag.CORE_NAME_UNCERTAIN
    return None


def normalize_risk_flags_in_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload

    normalized_payload = dict(payload)

    risk_flags = normalized_payload.get("risk_flags")
    if isinstance(risk_flags, list):
        normalized_payload["risk_flags"] = [_normalize_risk_flag_value(value) for value in risk_flags]

    return normalized_payload


def normalize_candidate_assessment_payload(payload: object) -> object:
    return normalize_risk_flags_in_payload(payload)


def normalize_model_decision_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload

    normalized_payload = normalize_risk_flags_in_payload(payload)

    candidate_assessments = normalized_payload.get("candidate_assessments")
    if isinstance(candidate_assessments, list):
        normalized_payload["candidate_assessments"] = [
            normalize_candidate_assessment_payload(assessment) for assessment in candidate_assessments
        ]

    return normalized_payload


HARD_CONFLICT_RISKS = {
    RiskFlag.BRAND_CONFLICT,
    RiskFlag.SPEC_CONFLICT,
    RiskFlag.PACKAGE_CONFLICT,
    RiskFlag.UNIT_CONFLICT,
    RiskFlag.SERIES_OR_GRADE_CONFLICT,
    RiskFlag.REMARK_CHANGES_IDENTITY,
    RiskFlag.NEEDS_UNSTATED_ASSUMPTION,
    RiskFlag.MULTIPLE_VALID_CANDIDATES,
    RiskFlag.INSUFFICIENT_CUSTOMER_INFO,
}


class CustomerRecord(BaseModel):
    record_id: str
    source_row_number: int
    raw_fields: dict[str, str] = Field(default_factory=dict)
    mapped_fields: dict[str, str] = Field(default_factory=dict)


class CompanyProduct(BaseModel):
    product_id: str
    code: str
    name: str
    unit: str = ""
    alias: str = ""
    description: str = ""
    category_path: list[str] = Field(default_factory=list)
    raw_fields: dict[str, str] = Field(default_factory=dict)


class CandidateItem(BaseModel):
    candidate_id: str
    product: CompanyProduct
    candidate_sources: list[str] = Field(default_factory=list)
    candidate_notes: str = ""
    candidate_evidence: "CandidateEvidence" = Field(default_factory=lambda: CandidateEvidence())


class CandidateEvidence(BaseModel):
    name_terms: list[str] = Field(default_factory=list)
    spec_tokens: list[str] = Field(default_factory=list)
    unit: str = ""
    match_sources: list[str] = Field(default_factory=list)
    conflict_notes: list[str] = Field(default_factory=list)


class CandidateAssessment(BaseModel):
    candidate_id: str
    same_business_identity: bool
    matched_evidence: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    summary: str = ""

    def __init__(self, /, **data: object) -> None:
        normalized_data = normalize_candidate_assessment_payload(data) if _NORMALIZE_RISK_FLAGS.get() else data
        super().__init__(**normalized_data)

    @classmethod
    def model_validate(
        cls,
        obj: object,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, object] | None = None,
    ) -> "CandidateAssessment":
        token = _NORMALIZE_RISK_FLAGS.set(False)
        try:
            return super().model_validate(obj, strict=strict, from_attributes=from_attributes, context=context)
        finally:
            _NORMALIZE_RISK_FLAGS.reset(token)


class ModelDecision(BaseModel):
    customer_semantic_summary: str
    key_identity_signals: list[str] = Field(default_factory=list)
    strong_constraints: list[str] = Field(default_factory=list)
    weak_constraints: list[str] = Field(default_factory=list)
    ignored_or_noise_signals: list[str] = Field(default_factory=list)
    missing_or_uncertain_signals: list[str] = Field(default_factory=list)
    candidate_assessments: list[CandidateAssessment] = Field(default_factory=list)
    selected_candidate_id: str | None = None
    result_status: ResultStatus
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    evidence_summary: str = ""
    manual_review_reason: str = ""
    can_auto_code: bool = False

    def __init__(self, /, **data: object) -> None:
        normalized_data = normalize_model_decision_payload(data) if _NORMALIZE_RISK_FLAGS.get() else data
        super().__init__(**normalized_data)

    @classmethod
    def model_validate(
        cls,
        obj: object,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, object] | None = None,
    ) -> "ModelDecision":
        token = _NORMALIZE_RISK_FLAGS.set(False)
        try:
            return super().model_validate(obj, strict=strict, from_attributes=from_attributes, context=context)
        finally:
            _NORMALIZE_RISK_FLAGS.reset(token)

    def _selected_assessment(self) -> CandidateAssessment | None:
        if not self.selected_candidate_id:
            return None
        return next(
            (
                assessment
                for assessment in self.candidate_assessments
                if assessment.candidate_id == self.selected_candidate_id
            ),
            None,
        )

    @model_validator(mode="after")
    def validate_auto_code_boundaries(self) -> "ModelDecision":
        if self.can_auto_code and self.result_status in {
            ResultStatus.SUGGESTED_CODE,
            ResultStatus.MANUAL_REVIEW,
            ResultStatus.UNMATCHED,
            ResultStatus.MODEL_ERROR,
        }:
            raise ValueError("suggested, manual, unmatched, and error results cannot auto-code")

        if self.can_auto_code:
            if not self.selected_candidate_id:
                raise ValueError("auto-code requires a selected candidate")

            selected_assessment = self._selected_assessment()
            if selected_assessment is None:
                raise ValueError("auto-code requires selected candidate assessment")
            if not selected_assessment.same_business_identity:
                raise ValueError("auto-code requires same business identity")

            selected_risks = set(selected_assessment.risk_flags)
            hard_risks = set(self.risk_flags).union(selected_risks).intersection(HARD_CONFLICT_RISKS)
            if hard_risks:
                raise ValueError("auto-code cannot contain hard conflict risks")

        if self.result_status == ResultStatus.STRONG_AUTO_CODE:
            if not self.can_auto_code:
                raise ValueError("strong auto-code requires can_auto_code=true")
            if not self.selected_candidate_id:
                raise ValueError("strong auto-code requires a selected candidate")

            selected_assessment = self._selected_assessment()
            if selected_assessment is None:
                raise ValueError("strong auto-code requires selected candidate assessment")
            if not selected_assessment.same_business_identity:
                raise ValueError("strong auto-code requires same business identity")

            selected_risks = set(selected_assessment.risk_flags)
            hard_risks = set(self.risk_flags).union(selected_risks).intersection(HARD_CONFLICT_RISKS)
            if hard_risks:
                raise ValueError("strong auto-code cannot contain hard conflict risks")

        if self.result_status == ResultStatus.UNMATCHED and self.selected_candidate_id:
            raise ValueError("unmatched cannot select a candidate")

        return self
