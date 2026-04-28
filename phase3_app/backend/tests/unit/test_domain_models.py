from product_code_mapper.domain.models import CompanyProduct, CustomerItem
from product_code_mapper.domain.statuses import MatchStatus


def test_match_status_values_are_chinese_business_states():
    assert MatchStatus.AUTO_CODE.value == "自动落码"
    assert MatchStatus.MANUAL_REVIEW.value == "必须人工审核"


def test_customer_item_keeps_original_row_data():
    item = CustomerItem(
        row_id="row-1",
        original_row_index=2,
        fields={"商品名称": "海天金标生抽", "规格": "500ml", "单位": "瓶"},
    )

    assert item.display_text == "海天金标生抽 500ml 瓶"


def test_company_product_has_required_identity_fields():
    product = CompanyProduct(
        code="P001",
        name="海天金标生抽",
        brand="海天",
        spec="500ml",
        unit="瓶",
    )

    assert product.identity_text == "海天 海天金标生抽 500ml 瓶"
