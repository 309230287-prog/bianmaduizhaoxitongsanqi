from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from product_code_mapper.domain.models import Candidate, CustomerItem


@dataclass(frozen=True)
class AutoCodeDecision:
    can_auto_code: bool
    block_reasons: list[str] = field(default_factory=list)


class AutoCodeGate:
    minimum_candidate_score = 80

    def evaluate(
        self,
        customer: CustomerItem,
        candidate: Candidate,
        evidence: dict[str, Any],
    ) -> AutoCodeDecision:
        block_reasons: list[str] = []

        if candidate.score < self.minimum_candidate_score:
            block_reasons.append("候选分不足")

        if not str(evidence.get("reason", "")).strip():
            block_reasons.append("缺少证据理由")

        product = candidate.product
        customer_text = customer.display_text
        customer_name = str(customer.fields.get("商品名称", "")).strip()

        if customer_name and product.name not in customer_text and customer_name not in product.identity_text:
            block_reasons.append("品名")

        for field_name, product_value in [
            ("品牌", product.brand),
            ("规格", product.spec),
            ("单位", product.unit),
            ("包装", product.package),
        ]:
            customer_value = str(customer.fields.get(field_name, "")).strip()
            if customer_value and product_value and customer_value != product_value:
                block_reasons.append(field_name)

        return AutoCodeDecision(
            can_auto_code=not block_reasons,
            block_reasons=_deduplicate(block_reasons),
        )


def _deduplicate(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result

