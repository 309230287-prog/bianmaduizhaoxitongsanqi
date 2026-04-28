from product_code_mapper.domain.models import Candidate, CompanyProduct, CustomerItem
from product_code_mapper.matching.auto_code_gate import AutoCodeGate


def test_gate_allows_exact_identity_match():
    customer = CustomerItem(
        row_id="row-1",
        original_row_index=2,
        fields={
            "商品名称": "海天金标生抽",
            "品牌": "海天",
            "规格": "500ml",
            "单位": "瓶",
        },
    )
    product = CompanyProduct(
        code="P1",
        name="海天金标生抽",
        brand="海天",
        spec="500ml",
        unit="瓶",
    )

    decision = AutoCodeGate().evaluate(
        customer,
        Candidate(product=product, score=100),
        evidence={
            "reason": "品牌、品名、规格、单位一致",
            "matched_signals": ["品牌", "品名", "规格", "单位"],
        },
    )

    assert decision.can_auto_code
    assert not decision.block_reasons


def test_gate_blocks_spec_conflict():
    customer = CustomerItem(
        row_id="row-1",
        original_row_index=2,
        fields={
            "商品名称": "海天金标生抽",
            "品牌": "海天",
            "规格": "500ml",
            "单位": "瓶",
        },
    )
    product = CompanyProduct(
        code="P2",
        name="海天金标生抽",
        brand="海天",
        spec="1.9L",
        unit="桶",
    )

    decision = AutoCodeGate().evaluate(
        customer,
        Candidate(product=product, score=95),
        evidence={"reason": "模型认为相似"},
    )

    assert not decision.can_auto_code
    assert "规格" in decision.block_reasons
