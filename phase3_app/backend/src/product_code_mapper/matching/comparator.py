"""Candidate comparator — model-based comparison of customer items vs. candidates.

The comparator bridges the model client and the structured CompareResult.
It asks the model to judge whether each customer-candidate pair represents
the same business product identity.
"""

from dataclasses import dataclass, field
from typing import Any

from product_code_mapper.domain.models import Candidate, CustomerItem, MatchResult
from product_code_mapper.domain.statuses import MatchStatus
from product_code_mapper.matching.auto_code_gate import AutoCodeDecision, AutoCodeGate
from product_code_mapper.model.client import ModelClient, ModelClientError
from product_code_mapper.model.schemas import CompareResult, ModelOutputValidationError


@dataclass(frozen=True)
class ComparisonOutcome:
    """The outcome of comparing a customer item against candidates."""

    match_result: MatchResult
    model_compare_result: CompareResult | None = None
    used_model: bool = False
    error: str | None = None


class CandidateComparator:
    """Compares customer items with candidates, using the model for judgment."""

    def __init__(self, model_client: ModelClient, auto_code_gate: AutoCodeGate | None = None) -> None:
        self._client = model_client
        self._gate = auto_code_gate or AutoCodeGate()

    def compare(
        self,
        customer: CustomerItem,
        candidates: list[Candidate],
    ) -> ComparisonOutcome:
        """Compare a customer item against all candidates.

        If candidates are empty, returns NO_RELIABLE_MATCH immediately
        without calling the model.
        """
        if not candidates:
            return ComparisonOutcome(
                match_result=MatchResult(
                    row_id=customer.row_id,
                    status=MatchStatus.NO_RELIABLE_MATCH,
                    reason_summary="未找到任何候选商品",
                    evidence_summary="候选检索未返回任何结果",
                ),
                used_model=False,
            )

        try:
            cr = self._client.compare(customer, candidates)
        except (ModelClientError, ModelOutputValidationError) as exc:
            # Model call failed — enter manual review with the best local candidate
            best = candidates[0]
            gate_decision = self._gate.evaluate(
                customer,
                best,
                evidence={"reason": f"模型比较失败: {exc}"},
            )
            status = MatchStatus.AUTO_CODE if gate_decision.can_auto_code else MatchStatus.SUGGESTED_REVIEW
            return ComparisonOutcome(
                match_result=MatchResult(
                    row_id=customer.row_id,
                    status=status,
                    selected_candidate=best,
                    reason_summary=f"模型比较失败，使用本地安全门判断: {exc}",
                    evidence_summary=f"模型调用异常: {exc}",
                    risk_summary="模型比较未完成" + ("、".join(gate_decision.block_reasons) or ""),
                    audit={"model_error": str(exc), "gate_decision": gate_decision},
                ),
                used_model=True,
                error=str(exc),
            )

        return self._build_outcome(customer, candidates, cr)

    def _build_outcome(
        self,
        customer: CustomerItem,
        candidates: list[Candidate],
        cr: CompareResult,
    ) -> ComparisonOutcome:
        index = cr.selected_candidate_index
        if index < 0 or index >= len(candidates):
            return ComparisonOutcome(
                match_result=MatchResult(
                    row_id=customer.row_id,
                    status=MatchStatus.NO_RELIABLE_MATCH,
                    reason_summary=cr.reason_summary,
                    evidence_summary=cr.evidence_summary,
                    risk_summary=cr.risk_summary,
                    audit={
                        "model_status": cr.status,
                        "matched_signals": cr.matched_signals,
                        "conflict_signals": cr.conflict_signals,
                    },
                ),
                model_compare_result=cr,
                used_model=True,
            )

        selected = candidates[index]
        gate_decision = self._gate.evaluate(
            customer,
            selected,
            evidence={
                "reason": cr.reason_summary,
                "evidence_summary": cr.evidence_summary,
                "matched_signals": cr.matched_signals,
                "conflict_signals": cr.conflict_signals,
            },
        )

        # Resolve final status: system gate overrides model
        if not gate_decision.can_auto_code:
            final_status = MatchStatus.MANUAL_REVIEW
            reason = f"系统安全门拦截: {'、'.join(gate_decision.block_reasons)}"
            risk = cr.risk_summary + f" 安全门拦截原因: {reason}" if cr.risk_summary else reason
        else:
            final_status = MatchStatus(cr.status)
            reason = cr.reason_summary
            risk = cr.risk_summary

        return ComparisonOutcome(
            match_result=MatchResult(
                row_id=customer.row_id,
                status=final_status,
                selected_candidate=selected,
                reason_summary=reason,
                evidence_summary=cr.evidence_summary,
                risk_summary=risk,
                audit={
                    "model_status": cr.status,
                    "matched_signals": cr.matched_signals,
                    "unmatched_signals": cr.unmatched_signals,
                    "conflict_signals": cr.conflict_signals,
                    "gate_block_reasons": gate_decision.block_reasons,
                    "gate_can_auto_code": gate_decision.can_auto_code,
                },
            ),
            model_compare_result=cr,
            used_model=True,
        )
