from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from product_code_mapper.candidates.executor import CandidateExecutor
from product_code_mapper.domain.models import CompanyProduct, CustomerItem, MatchResult
from product_code_mapper.domain.statuses import MatchStatus
from product_code_mapper.matching.auto_code_gate import AutoCodeGate
from product_code_mapper.matching.comparator import CandidateComparator, ComparisonOutcome
from product_code_mapper.model.client import FakeModelClient
from product_code_mapper.planning.round_command import RoundCommandValidationError
from product_code_mapper.planning.round_planner import RoundPlanner
from product_code_mapper.planning.round_command import RoundCommand
from product_code_mapper.pool.nature_pool import NaturePool
from product_code_mapper.runs.audit_trail import AuditEntry, AuditTrail
from product_code_mapper.runs.metrics import RunMetrics
from product_code_mapper.runs.state_machine import RunStateMachine, RunStatus

MAX_TOTAL_ROUNDS = 10
ProgressCallback = Callable[[dict[str, MatchResult], int, int], None]


@dataclass(frozen=True)
class MatchRunResult:
    metrics: RunMetrics
    audit_entries: list[AuditEntry]
    row_results: dict[str, MatchResult]
    customer_items: list[CustomerItem] = field(default_factory=list)
    total_rounds: int = 0


class MatchRunEngine:
    def __init__(self, model_client, auto_code_gate: AutoCodeGate | None = None) -> None:
        self._model_client = model_client
        self._auto_code_gate = auto_code_gate or AutoCodeGate()

    def run_once(
        self,
        customer_items: list[CustomerItem],
        company_products: list[CompanyProduct],
    ) -> MatchRunResult:
        """Run a single round (existing contract kept for backward compat)."""
        command = _build_fallback_round_command(customer_items)
        pool = NaturePool(customer_items)
        audit = AuditTrail()
        candidate_executor = CandidateExecutor(company_products)
        comparator = CandidateComparator(self._model_client, self._auto_code_gate)
        row_results: dict[str, MatchResult] = {}

        for item in customer_items:
            outcome = _process_item(item, command, candidate_executor, comparator, pool, audit)
            row_results[item.row_id] = outcome.match_result

        metrics = RunMetrics(
            total_count=len(customer_items),
            auto_code_count=_count_status(row_results, MatchStatus.AUTO_CODE),
            auto_code_with_diff_count=_count_status(row_results, MatchStatus.AUTO_CODE_WITH_DIFFERENCE),
            suggested_review_count=_count_status(row_results, MatchStatus.SUGGESTED_REVIEW),
            manual_review_count=_count_status(row_results, MatchStatus.MANUAL_REVIEW),
            no_reliable_match_count=_count_status(row_results, MatchStatus.NO_RELIABLE_MATCH),
            returned_to_nature_count=len(pool.remaining_row_ids),
            hard_case_count=len(pool.hard_case_row_ids),
            total_rounds=1,
        )
        return MatchRunResult(
            metrics=metrics,
            audit_entries=audit.entries,
            row_results=row_results,
            customer_items=customer_items,
            total_rounds=1,
        )

    def run_full(
        self,
        customer_items: list[CustomerItem],
        company_products: list[CompanyProduct],
        *,
        max_rounds: int = MAX_TOTAL_ROUNDS,
        state_machine: RunStateMachine | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> MatchRunResult:
        """Run the full multi-round 003 flow.

        Each round: model plans → system executes → auto-code gate →
        complete or return to nature. Continues until no items remain or
        max rounds is reached.
        """
        company_codes = frozenset(p.code for p in company_products)
        gate = AutoCodeGate(company_codes)
        comparator = CandidateComparator(self._model_client, gate)
        candidate_executor = CandidateExecutor(company_products)
        pool = NaturePool(customer_items, max_rounds_per_item=5)
        audit = AuditTrail()
        row_results: dict[str, MatchResult] = {}
        planner = RoundPlanner(self._model_client)
        completed_dimensions: list[str] = []
        round_no = 0

        for round_no in range(1, max_rounds + 1):
            remaining_ids = pool.remaining_row_ids
            if not remaining_ids:
                break

            remaining_items = [
                item for item in customer_items if item.row_id in remaining_ids
            ]

            plan_result = planner.plan_next_round(
                remaining_items=remaining_items,
                completed_dimensions=completed_dimensions,
                round_no=round_no,
            )

            if plan_result.command is None:
                breakdown_items = [
                    item for item in customer_items
                    if item.row_id in remaining_ids and item.row_id not in pool.hard_case_row_ids
                ]
                if breakdown_items:
                    fallback_command = _build_fallback_round_command(breakdown_items)
                    for item in breakdown_items:
                        if not pool.can_enter_dimension(item.row_id, fallback_command.entry_dimension):
                            continue
                        outcome = _process_item(
                            item, fallback_command, candidate_executor, comparator, pool, audit, round_no
                        )
                        row_results[item.row_id] = outcome.match_result
                        if progress_callback:
                            progress_callback(row_results, round_no, len(customer_items))
                    completed_dimensions.append(fallback_command.entry_dimension)
                audit.add("system", "planner_fallback", f"第 {round_no} 轮模型发令失败，使用回退命令: {plan_result.error}")
                continue

            command = plan_result.command
            completed_dimensions = list(plan_result.dimensions_used)
            audit.add("system", "round_plan", f"第 {round_no} 轮: {command.round_name}", command_dimension=command.entry_dimension)

            for item in customer_items:
                if state_machine and state_machine.should_stop:
                    break
                if state_machine and state_machine.should_pause:
                    state_machine.confirm_paused()
                    state_machine.wait_if_paused()
                    if state_machine.should_stop:
                        break
                if item.row_id not in remaining_ids:
                    continue
                if not pool.can_enter_dimension(item.row_id, command.entry_dimension):
                    continue

                outcome = _process_item(item, command, candidate_executor, comparator, pool, audit, round_no)
                row_results[item.row_id] = outcome.match_result
                if progress_callback:
                    progress_callback(row_results, round_no, len(customer_items))

            if state_machine and state_machine.should_stop:
                break

        # Mark remaining items as hard cases or no match
        for item in customer_items:
            if item.row_id not in row_results:
                if item.row_id in pool.hard_case_row_ids:
                    row_results[item.row_id] = MatchResult(
                        row_id=item.row_id,
                        status=MatchStatus.MANUAL_REVIEW,
                        reason_summary="多轮仍未完成，进入疑难池",
                        evidence_summary=f"经过 {pool.return_records_for(item.row_id)} 轮尝试",
                        audit={"rounds_attempted": len(pool.return_records_for(item.row_id))},
                    )
                else:
                    row_results[item.row_id] = MatchResult(
                        row_id=item.row_id,
                        status=MatchStatus.NO_RELIABLE_MATCH,
                    )

        metrics = RunMetrics(
            total_count=len(customer_items),
            auto_code_count=_count_status(row_results, MatchStatus.AUTO_CODE),
            auto_code_with_diff_count=_count_status(row_results, MatchStatus.AUTO_CODE_WITH_DIFFERENCE),
            suggested_review_count=_count_status(row_results, MatchStatus.SUGGESTED_REVIEW),
            manual_review_count=_count_status(row_results, MatchStatus.MANUAL_REVIEW),
            no_reliable_match_count=_count_status(row_results, MatchStatus.NO_RELIABLE_MATCH),
            returned_to_nature_count=len(pool.remaining_row_ids),
            hard_case_count=len(pool.hard_case_row_ids),
            total_rounds=round_no,
        )
        return MatchRunResult(
            metrics=metrics,
            audit_entries=audit.entries,
            row_results=row_results,
            customer_items=customer_items,
            total_rounds=round_no,
        )


def _process_item(
    item: CustomerItem,
    command,
    candidate_executor: CandidateExecutor,
    comparator: CandidateComparator,
    pool: NaturePool,
    audit: AuditTrail,
    round_no: int = 1,
) -> ComparisonOutcome:
    candidates = candidate_executor.find_candidates(item, command)

    if not candidates:
        pool.record_return(item.row_id, dimension=command.entry_dimension, reason="未找到候选")
        audit.add(item.row_id, "return_to_nature", f"第{round_no}轮 未找到候选，回到大自然池")
        return ComparisonOutcome(
            match_result=MatchResult(
                row_id=item.row_id,
                status=MatchStatus.NO_RELIABLE_MATCH,
                reason_summary=f"第{round_no}轮 在维度 {command.entry_dimension} 下未找到候选",
            ),
        )

    outcome = comparator.compare(item, candidates)
    result = outcome.match_result

    if result.status == MatchStatus.AUTO_CODE:
        pool.mark_completed(item.row_id)
        audit.add(
            item.row_id,
            "auto_code",
            f"第{round_no}轮 通过自动落码安全门",
            product_code=result.selected_candidate.product.code if result.selected_candidate else "",
        )
    elif result.status == MatchStatus.NO_RELIABLE_MATCH:
        pool.record_return(item.row_id, dimension=command.entry_dimension, reason="无可靠候选")
        audit.add(item.row_id, "return_to_nature", f"第{round_no}轮 无可靠匹配，回到大自然池")
    else:
        pool.record_return(
            item.row_id,
            dimension=command.entry_dimension,
            reason=result.risk_summary or "需人工审核",
        )
        audit.add(
            item.row_id,
            "return_to_nature",
            f"第{round_no}轮 安全门未放行，回到大自然池",
            status=result.status.value,
            block_info=result.risk_summary,
        )

    return outcome


def _build_fallback_round_command(customer_items: list[CustomerItem]):
    sample_terms = _sample_terms(customer_items)
    payload = FakeModelClient().plan_round({"sample_terms": sample_terms})
    return RoundCommand.from_payload(payload)


def _sample_terms(customer_items: list[CustomerItem]) -> list[str]:
    for marker in ["生抽", "老抽", "番茄", "酱油", "醋", "料酒", "蚝油"]:
        if any(marker in item.display_text for item in customer_items):
            return [marker]
    if customer_items:
        return [str(customer_items[0].fields.get("商品名称", "未分类商品")).strip() or "未分类商品"]
    return ["未分类商品"]


def _count_status(results: dict[str, MatchResult], status: MatchStatus) -> int:
    return sum(1 for r in results.values() if r.status == status)
