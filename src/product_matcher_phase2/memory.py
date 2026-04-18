from __future__ import annotations

from enum import Enum
from typing import Iterable

from pydantic import BaseModel, Field, model_validator

from product_matcher_phase2.schemas import CustomerRecord, RiskFlag


class MemoryType(str, Enum):
    TASK = "task"
    MANUAL_CONFIRMATION = "manual_confirmation"
    CUSTOMER_EXPRESSION_PATTERN = "customer_expression_pattern"
    PRODUCT_SEMANTIC = "product_semantic"
    BUSINESS_EQUIVALENCE = "business_equivalence"
    FAILURE_CASE = "failure_case"


class MemoryScope(str, Enum):
    GLOBAL = "global"
    CUSTOMER_SPECIFIC = "customer_specific"
    CATEGORY_SPECIFIC = "category_specific"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    NEEDS_REVIEW = "needs_review"


class ProductMemoryItem(BaseModel):
    memory_id: str
    memory_type: MemoryType
    scope: MemoryScope
    source_text: str
    normalized_meaning: str
    customer_id: str | None = None
    company_product_id: str | None = None
    applicable_conditions: dict[str, str] = Field(default_factory=dict)
    confidence_level: str
    can_support_weak_auto_code: bool = False
    created_from_record_id: str
    created_by: str
    status: MemoryStatus = MemoryStatus.ACTIVE
    risk_flags: list[RiskFlag] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_memory_source(self) -> "ProductMemoryItem":
        if self.can_support_weak_auto_code:
            if self.confidence_level != "confirmed" or self.created_by == "model":
                raise ValueError("weak-auto memory must come from human confirmation")
        return self

    def applies_to(self, record: CustomerRecord, customer_id: str | None = None) -> bool:
        if self.status != MemoryStatus.ACTIVE:
            return False

        if self.scope == MemoryScope.CUSTOMER_SPECIFIC and self.customer_id != customer_id:
            return False

        for field_name, expected_value in self.applicable_conditions.items():
            actual_value = record.mapped_fields.get(field_name, "")
            if actual_value != expected_value:
                return False

        if self.applicable_conditions:
            return True

        if not self.source_text:
            return True

        return any(self.source_text in value for value in record.mapped_fields.values())


def find_applicable_memories(
    record: CustomerRecord,
    memories: Iterable[ProductMemoryItem],
    customer_id: str | None = None,
) -> list[ProductMemoryItem]:
    return [memory for memory in memories if memory.applies_to(record, customer_id=customer_id)]


def should_block_strong_auto_code(
    memories: Iterable[ProductMemoryItem],
    risk_flags: Iterable[RiskFlag],
) -> bool:
    current_risks = set(risk_flags)
    for memory in memories:
        if memory.status != MemoryStatus.ACTIVE:
            continue
        if memory.memory_type != MemoryType.FAILURE_CASE:
            continue
        if current_risks.intersection(memory.risk_flags):
            return True
    return False
