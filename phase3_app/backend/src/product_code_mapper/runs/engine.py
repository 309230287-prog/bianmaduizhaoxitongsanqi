from __future__ import annotations

from dataclasses import dataclass

from product_code_mapper.candidates.executor import CandidateExecutor
from product_code_mapper.domain.models import CompanyProduct, CustomerItem, MatchResult
from product_code_mapper.domain.statuses import MatchStatus
from product_code_mapper.matching.auto_code_gate import AutoCodeGate
from product_code_mapper.planning.round_command import RoundCommand
from product_code_mapper.pool.nature_pool import NaturePool
from product_code_mapper.runs.audit_trail import AuditEntry, AuditTrail
from product_code_mapper.runs.metrics import RunMetrics


@dataclass(frozen=True)
class MatchRunResult:
    metrics: RunMetrics
    audit_entries: list[AuditEntry]
    row_results: list[MatchResult]


class MatchRunEngine:
    def __init__(self, model_client, auto_code_gate: AutoCodeGate | None = None) -> None:
        self._model_client = model_client
        self._auto_code_gate = auto_code_gate or AutoCodeGate()

    def run_once(
        self,
        customer_items: list[CustomerItem],
        company_products: list[CompanyProduct],
    ) -> MatchRunResult:
        command = RoundCommand.from_payload(
            self._model_client.plan_round(
                remaining_items_summary={"sample_terms": _sample_terms(customer_items)}
            )
        )
        pool = NaturePool(customer_items)
        audit = AuditTrail()
        candidate_executor = CandidateExecutor(company_products)
        row_results: list[MatchResult] = []

        for item in customer_items:
            candidates = candidate_executor.find_candidates(item, command)
            if not candidates:
                pool.record_return(item.row_id, dimension=command.entry_dimension, reason="未找到候选")
                audit.add(item.row_id, "return_to_nature", "未找到候选，回到大自然池")
                row_results.append(
                    MatchResult(row_id=item.row_id, status=MatchStatus.NO_RELIABLE_MATCH)
                )
                continue

            best_candidate = candidates[0]
            decision = self._auto_code_gate.evaluate(
                item,
                best_candidate,
                evidence={"reason": "候选召回后通过系统安全门判断"},
            )
            if decision.can_auto_code:
                pool.mark_completed(item.row_id)
                audit.add(
                    item.row_id,
                    "auto_code",
                    "通过自动落码安全门",
                    product_code=best_candidate.product.code,
                )
                row_results.append(
                    MatchResult(
                        row_id=item.row_id,
                        status=MatchStatus.AUTO_CODE,
                        selected_candidate=best_candidate,
                        reason_summary="品牌、品名、规格、单位未发现硬冲突",
                    )
                )
                continue

            reason = "、".join(decision.block_reasons) or "证据不足"
            pool.record_return(item.row_id, dimension=command.entry_dimension, reason=reason)
            audit.add(
                item.row_id,
                "return_to_nature",
                "安全门未放行，回到大自然池",
                block_reasons=decision.block_reasons,
            )
            row_results.append(
                MatchResult(
                    row_id=item.row_id,
                    status=MatchStatus.SUGGESTED_REVIEW,
                    selected_candidate=best_candidate,
                    risk_summary=reason,
                )
            )

        metrics = RunMetrics(
            total_count=len(customer_items),
            auto_code_count=sum(1 for result in row_results if result.status == MatchStatus.AUTO_CODE),
            returned_to_nature_count=len(pool.remaining_row_ids),
            hard_case_count=len(pool.hard_case_row_ids),
        )
        return MatchRunResult(
            metrics=metrics,
            audit_entries=audit.entries,
            row_results=row_results,
        )


def _sample_terms(customer_items: list[CustomerItem]) -> list[str]:
    if any("生抽" in item.display_text for item in customer_items):
        return ["生抽"]
    if not customer_items:
        return ["未分类商品"]
    return [str(customer_items[0].fields.get("商品名称", "未分类商品")).strip() or "未分类商品"]

