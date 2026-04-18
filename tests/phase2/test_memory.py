import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.memory import (
    MemoryScope,
    MemoryStatus,
    MemoryType,
    ProductMemoryItem,
    find_applicable_memories,
    should_block_strong_auto_code,
)
from product_matcher_phase2.schemas import CustomerRecord, RiskFlag


class ProductMemoryTests(unittest.TestCase):
    def test_weak_auto_memory_requires_human_confirmed_source(self) -> None:
        with self.assertRaises(ValidationError):
            ProductMemoryItem(
                memory_id="M000001",
                memory_type=MemoryType.PRODUCT_SEMANTIC,
                scope=MemoryScope.GLOBAL,
                source_text="听装",
                normalized_meaning="罐装",
                confidence_level="model_suggested",
                can_support_weak_auto_code=True,
                created_from_record_id="C000001",
                created_by="model",
                status=MemoryStatus.ACTIVE,
            )

    def test_manual_confirmation_applies_when_conditions_match(self) -> None:
        memory = ProductMemoryItem(
            memory_id="M000002",
            memory_type=MemoryType.MANUAL_CONFIRMATION,
            scope=MemoryScope.CUSTOMER_SPECIFIC,
            customer_id="客户A",
            source_text="听装可乐",
            normalized_meaning="罐装可口可乐",
            company_product_id="SPU123",
            applicable_conditions={"unit": "件", "category": "饮料类"},
            confidence_level="confirmed",
            can_support_weak_auto_code=True,
            created_from_record_id="C000002",
            created_by="人工审核",
            status=MemoryStatus.ACTIVE,
        )
        record = CustomerRecord(
            record_id="C000010",
            source_row_number=10,
            raw_fields={},
            mapped_fields={"name": "听装可乐", "unit": "件", "category": "饮料类"},
        )

        self.assertTrue(memory.applies_to(record, customer_id="客户A"))

    def test_memory_does_not_apply_when_key_condition_conflicts(self) -> None:
        memory = ProductMemoryItem(
            memory_id="M000003",
            memory_type=MemoryType.MANUAL_CONFIRMATION,
            scope=MemoryScope.CUSTOMER_SPECIFIC,
            customer_id="客户A",
            source_text="可口可乐",
            normalized_meaning="可口可乐330ml罐装",
            company_product_id="SPU123",
            applicable_conditions={"unit": "件", "spec": "330ml"},
            confidence_level="confirmed",
            can_support_weak_auto_code=True,
            created_from_record_id="C000003",
            created_by="人工审核",
            status=MemoryStatus.ACTIVE,
        )
        record = CustomerRecord(
            record_id="C000011",
            source_row_number=11,
            raw_fields={},
            mapped_fields={"name": "可口可乐", "unit": "瓶", "spec": "330ml"},
        )

        self.assertFalse(memory.applies_to(record, customer_id="客户A"))

    def test_find_applicable_memories_filters_inactive_and_wrong_customer(self) -> None:
        active = ProductMemoryItem(
            memory_id="M000004",
            memory_type=MemoryType.CUSTOMER_EXPRESSION_PATTERN,
            scope=MemoryScope.CUSTOMER_SPECIFIC,
            customer_id="客户A",
            source_text="件",
            normalized_meaning="该客户常用件表示整箱单位",
            confidence_level="confirmed",
            can_support_weak_auto_code=False,
            created_from_record_id="C000004",
            created_by="人工审核",
            status=MemoryStatus.ACTIVE,
        )
        wrong_customer = active.model_copy(update={"memory_id": "M000005", "customer_id": "客户B"})
        inactive = active.model_copy(update={"memory_id": "M000006", "status": MemoryStatus.DISABLED})
        record = CustomerRecord(
            record_id="C000012",
            source_row_number=12,
            raw_fields={},
            mapped_fields={"name": "可口可乐", "unit": "件"},
        )

        applicable = find_applicable_memories(
            record,
            memories=[active, wrong_customer, inactive],
            customer_id="客户A",
        )

        self.assertEqual([item.memory_id for item in applicable], ["M000004"])

    def test_failure_memory_blocks_strong_auto_when_risk_matches(self) -> None:
        failure_memory = ProductMemoryItem(
            memory_id="F000001",
            memory_type=MemoryType.FAILURE_CASE,
            scope=MemoryScope.GLOBAL,
            source_text="1*24*330ml",
            normalized_meaning="多层包装不能压成单罐规格",
            confidence_level="confirmed",
            can_support_weak_auto_code=False,
            created_from_record_id="C000005",
            created_by="人工复盘",
            status=MemoryStatus.ACTIVE,
            risk_flags=[RiskFlag.PACKAGE_CONFLICT],
        )

        self.assertTrue(
            should_block_strong_auto_code(
                memories=[failure_memory],
                risk_flags=[RiskFlag.PACKAGE_CONFLICT],
            )
        )


if __name__ == "__main__":
    unittest.main()
