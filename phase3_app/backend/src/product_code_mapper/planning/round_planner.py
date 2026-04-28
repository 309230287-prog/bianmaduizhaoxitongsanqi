"""Round planner — calls the model to generate structured batch commands.

The RoundPlanner bridges the model client and RoundCommand validation.
It asks the model to look at the remaining nature pool and decide the next
round's entry dimension, terms, and strategy.
"""

from dataclasses import dataclass, field
from typing import Any

from product_code_mapper.domain.models import CustomerItem
from product_code_mapper.model.client import ModelClient, ModelClientError
from product_code_mapper.planning.round_command import RoundCommand, RoundCommandValidationError


@dataclass(frozen=True)
class PlanResult:
    """Result of a round planning attempt."""

    command: RoundCommand | None = None
    error: str | None = None
    dimensions_used: list[str] = field(default_factory=list)


class RoundPlanner:
    """Plans processing rounds by calling the model to analyze the nature pool."""

    def __init__(self, model_client: ModelClient) -> None:
        self._client = model_client

    def plan_next_round(
        self,
        remaining_items: list[CustomerItem],
        completed_dimensions: list[str],
        round_no: int,
    ) -> PlanResult:
        """Ask the model for the next round command.

        Returns a PlanResult with either a valid RoundCommand or an error.
        """
        if not remaining_items:
            return PlanResult(error="大自然池已无剩余商品")

        sample_items = remaining_items[:20]
        try:
            payload = self._client.plan_round(
                remaining_count=len(remaining_items),
                sample_items=sample_items,
                completed_dimensions=completed_dimensions,
                round_no=round_no,
            )
        except ModelClientError as exc:
            return PlanResult(
                error=f"模型发令调用失败: {exc}",
                dimensions_used=list(completed_dimensions),
            )

        try:
            command = RoundCommand.from_payload(payload)
        except RoundCommandValidationError as exc:
            return PlanResult(
                error=f"模型发令校验不通过: {exc}",
                dimensions_used=list(completed_dimensions),
            )

        new_dimensions = list(completed_dimensions) + [command.entry_dimension]
        return PlanResult(command=command, dimensions_used=new_dimensions)
