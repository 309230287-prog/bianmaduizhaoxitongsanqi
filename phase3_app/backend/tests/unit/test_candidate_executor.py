from product_code_mapper.candidates.executor import CandidateExecutor
from product_code_mapper.domain.models import CompanyProduct, CustomerItem
from product_code_mapper.planning.round_command import RoundCommand


def sinh_round_command():
    return RoundCommand.from_payload(
        {
            "round_id": "round_001",
            "round_name": "核心品名_生抽",
            "round_goal": "处理生抽",
            "entry_dimension": "core_product_name",
            "entry_terms": ["生抽"],
            "exclude_terms": ["老抽"],
            "must_check_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
            "hard_conflict_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
            "search_strategy": {
                "company_catalog_scope": "global",
                "candidate_limit": 20,
                "export_candidate_limit": 5,
            },
            "model_compare_policy": "compare_only_after_candidates",
            "auto_code_policy": "system_gate_required",
        }
    )


def test_executor_uses_entry_terms_and_exclude_terms():
    products = [
        CompanyProduct(code="P1", name="海天金标生抽", brand="海天", spec="500ml", unit="瓶"),
        CompanyProduct(code="P2", name="海天老抽", brand="海天", spec="500ml", unit="瓶"),
    ]
    customer = CustomerItem(
        row_id="row-1",
        original_row_index=2,
        fields={"商品名称": "海天金标生抽", "规格": "500ml", "单位": "瓶"},
    )

    candidates = CandidateExecutor(products).find_candidates(customer, sinh_round_command())

    assert [candidate.product.code for candidate in candidates] == ["P1"]


def test_executor_boosts_brand_spec_and_unit_matches():
    products = [
        CompanyProduct(code="P1", name="金标生抽", brand="海天", spec="500ml", unit="瓶"),
        CompanyProduct(code="P2", name="金标生抽", brand="厨邦", spec="1L", unit="桶"),
    ]
    customer = CustomerItem(
        row_id="row-1",
        original_row_index=2,
        fields={"商品名称": "海天金标生抽", "品牌": "海天", "规格": "500ml", "单位": "瓶"},
    )

    candidates = CandidateExecutor(products).find_candidates(customer, sinh_round_command())

    assert candidates[0].product.code == "P1"
    assert candidates[0].score > candidates[1].score
