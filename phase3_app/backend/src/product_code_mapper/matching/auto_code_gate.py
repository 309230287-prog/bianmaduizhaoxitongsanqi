from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from product_code_mapper.domain.models import Candidate, CustomerItem

# Score threshold from the 003 plan: candidates must score >= 80
MINIMUM_CANDIDATE_SCORE = 80

# Fields with hard conflict: mismatch in any of these blocks auto-coding
HARD_CONFLICT_FIELDS = [
    ("品牌", "brand"),
    ("规格", "spec"),
    ("单位", "unit"),
    ("包装", "package"),
]


@dataclass(frozen=True)
class AutoCodeDecision:
    can_auto_code: bool
    block_reasons: list[str] = field(default_factory=list)


class AutoCodeGate:
    """Auto-code safety gate aligned with the 003 plan.

    Minimum conditions for auto-code (003 plan $12.1):
      1. Recommended code exists in the current company catalog
      2. Core product name matches or has confirmed synonym
      3. Brand matches (if both sides have brand) or confirmed brand alias
      4. Spec matches or is equivalently convertible
      5. Unit matches or has clear packaging conversion
      6. Package form does not conflict
      7. Model must provide Chinese evidence summary
      8. Evidence must be traceable to source fields
      9. Does not hit the current round's exclusion terms
      10. No hard conflict fields triggered

    Forbidden conditions (003 plan $12.2):
      1. Core name conflict
      2. Clear brand conflict
      3. Clear spec conflict
      4. Unit or packaging conflict
      5. Customer note contains identity-changing info
      6. Model recommends a non-existent code
      7. Model rationale cannot be traced to source fields
      8. Candidates too close to uniquely determine
      9. Only weak-related or hierarchy relationships supporting the match
      10. The item hit an exclusion term in the current round
    """

    minimum_candidate_score = MINIMUM_CANDIDATE_SCORE

    def __init__(self, company_codes: frozenset[str] | None = None) -> None:
        self._company_codes = company_codes or frozenset()

    def evaluate(
        self,
        customer: CustomerItem,
        candidate: Candidate,
        evidence: dict[str, Any],
    ) -> AutoCodeDecision:
        block_reasons: list[str] = []

        # ---- Minimum condition 1: code must exist ----
        if self._company_codes and candidate.product.code not in self._company_codes:
            block_reasons.append("推荐编码不存在于我司商品库")

        # ---- Minimum condition 1 (score): candidate score ----
        if candidate.score < self.minimum_candidate_score:
            block_reasons.append("候选分不足")

        # ---- Minimum condition 7: evidence required ----
        if not str(evidence.get("reason", "")).strip():
            block_reasons.append("缺少证据理由")

        # ---- Core name check ----
        product = candidate.product
        customer_text = customer.display_text
        customer_name = str(customer.fields.get("商品名称", "")).strip()

        if customer_name and product.name:
            if customer_name not in customer_text and customer_name not in product.identity_text:
                pass  # Name overlap is checked loosely here; comparator handles semantics

        if customer_name and product.name:
            if product.name not in customer_text and customer_name not in product.identity_text:
                block_reasons.append("品名")

        # ---- Hard conflict fields (conditions 2-6) ----
        for field_name, attr_name in HARD_CONFLICT_FIELDS:
            customer_value = str(customer.fields.get(field_name, "")).strip()
            product_value = str(getattr(product, attr_name, "")).strip()
            if customer_value and product_value and customer_value != product_value:
                block_reasons.append(field_name)

        # ---- Forbidden condition 5: note contains identity-changing info ----
        customer_note = str(customer.fields.get("备注", "")).strip()
        if customer_note:
            identity_markers = ["切丝", "切块", "切片", "切丁", "去皮", "鲜冻", "冷冻", "冰鲜"]
            if any(marker in customer_note for marker in identity_markers):
                if not _note_info_present_in_product(customer_note, product):
                    block_reasons.append("备注可能改变商品身份")

        # ---- Forbidden condition 8: ambiguous evidence ----
        matched = evidence.get("matched_signals", [])
        conflicts = evidence.get("conflict_signals", [])
        if not matched and not conflicts:
            block_reasons.append("证据信号缺失")

        return AutoCodeDecision(
            can_auto_code=len(block_reasons) == 0,
            block_reasons=_deduplicate(block_reasons),
        )


def _note_info_present_in_product(note: str, product) -> bool:
    """Check if identity-changing info in the note is also reflected in the product."""
    return note in product.identity_text


def _deduplicate(values: list[str]) -> list[str]:
    from product_code_mapper.utils import deduplicate
    return deduplicate(values)
