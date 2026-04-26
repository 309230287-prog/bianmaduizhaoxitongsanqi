from product_code_mapper.domain.models import CustomerItem
from product_code_mapper.pool.nature_pool import NaturePool


def test_item_moves_to_hard_case_after_five_rounds():
    item = CustomerItem(row_id="row-1", original_row_index=2, fields={"商品名称": "未知商品"})
    pool = NaturePool([item], max_rounds_per_item=5)

    for index in range(5):
        pool.record_return("row-1", dimension=f"dimension-{index}", reason="证据不足")

    assert "row-1" in pool.hard_case_row_ids


def test_same_dimension_can_only_be_used_twice():
    item = CustomerItem(row_id="row-1", original_row_index=2, fields={"商品名称": "未知商品"})
    pool = NaturePool([item], max_rounds_per_dimension=2)

    assert pool.can_enter_dimension("row-1", "brand")
    pool.record_return("row-1", dimension="brand", reason="候选不足")
    pool.record_return("row-1", dimension="brand", reason="候选不足")

    assert not pool.can_enter_dimension("row-1", "brand")


def test_completed_item_leaves_nature_pool():
    item = CustomerItem(row_id="row-1", original_row_index=2, fields={"商品名称": "海天金标生抽"})
    pool = NaturePool([item])

    pool.mark_completed("row-1")

    assert "row-1" not in pool.remaining_row_ids
