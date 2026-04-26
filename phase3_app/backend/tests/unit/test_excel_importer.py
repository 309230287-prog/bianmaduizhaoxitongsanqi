from pathlib import Path

from openpyxl import Workbook

from product_code_mapper.excel.importer import import_customer_items


def test_import_customer_items_keeps_chinese_columns(tmp_path: Path):
    workbook_path = tmp_path / "客户商品库.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["商品名称", "规格", "单位"])
    ws.append(["海天金标生抽", "500ml", "瓶"])
    wb.save(workbook_path)

    items = import_customer_items(workbook_path)

    assert items[0].row_id == "row-2"
    assert items[0].original_row_index == 2
    assert items[0].fields["商品名称"] == "海天金标生抽"
    assert items[0].fields["规格"] == "500ml"
    assert items[0].fields["单位"] == "瓶"

