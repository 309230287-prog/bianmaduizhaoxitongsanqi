from product_code_mapper.domain.models import CompanyProduct, CustomerItem
from product_code_mapper.model.client import FakeModelClient
from product_code_mapper.runs.engine import MatchRunEngine


def test_engine_auto_codes_clear_match_and_returns_uncertain_to_pool():
    company_products = [
        CompanyProduct(
            code="P1",
            name="海天金标生抽",
            brand="海天",
            spec="500ml",
            unit="瓶",
        ),
        CompanyProduct(code="P2", name="西红柿", brand="", spec="散称", unit="斤"),
    ]
    customer_items = [
        CustomerItem(
            row_id="row-1",
            original_row_index=2,
            fields={
                "商品名称": "海天金标生抽",
                "品牌": "海天",
                "规格": "500ml",
                "单位": "瓶",
            },
        ),
        CustomerItem(
            row_id="row-2",
            original_row_index=3,
            fields={"商品名称": "番茄酱", "规格": "500g", "单位": "瓶"},
        ),
    ]

    result = MatchRunEngine(model_client=FakeModelClient()).run_once(
        customer_items,
        company_products,
    )

    assert result.metrics.auto_code_count == 1
    assert result.metrics.returned_to_nature_count >= 1
    assert result.audit_entries

