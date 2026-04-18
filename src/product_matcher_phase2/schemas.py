from __future__ import annotations

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


class CandidateAssessment(BaseModel):
    candidate_id: str
    same_business_identity: bool
    matched_evidence: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    summary: str = ""


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
            ResultStatus.MANUAL_REVIEW,
            ResultStatus.UNMATCHED,
            ResultStatus.MODEL_ERROR,
        }:
            raise ValueError("manual, unmatched, and error results cannot auto-code")

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

        return self
