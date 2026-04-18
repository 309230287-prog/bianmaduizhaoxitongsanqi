import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.excel_loader import load_company_products, load_customer_records


class ExcelLoaderTests(unittest.TestCase):
    def _save_workbook(self, rows: list[list[object]]) -> Path:
        workbook = Workbook()
        worksheet = workbook.active
        for row in rows:
            worksheet.append(row)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "商品库测试.xlsx"
        workbook.save(path)
        return path

    def test_load_customer_records_preserves_duplicate_chinese_headers(self) -> None:
        path = self._save_workbook(
            [
                ["商品名称", "编号", "类别", "商品名称", "规格", "单位", ""],
                ["海天金标生抽原始列", "A001", "调味品", "海天金标生抽", "500ml", "瓶", "备注A"],
            ]
        )

        records = load_customer_records(path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].source_row_number, 2)
        self.assertEqual(records[0].raw_fields["商品名称"], "海天金标生抽原始列")
        self.assertEqual(records[0].raw_fields["商品名称_2"], "海天金标生抽")
        self.assertEqual(records[0].raw_fields["未命名列7"], "备注A")
        self.assertEqual(records[0].mapped_fields["name"], "海天金标生抽")
        self.assertEqual(records[0].mapped_fields["spec"], "500ml")
        self.assertEqual(records[0].mapped_fields["unit"], "瓶")
        self.assertEqual(records[0].mapped_fields["category"], "调味品")

    def test_load_customer_records_skips_blank_rows(self) -> None:
        path = self._save_workbook(
            [
                ["商品名称", "规格", "单位"],
                [None, None, None],
                ["王老吉凉茶", "1*24*250ml", "件"],
            ]
        )

        records = load_customer_records(path)

        self.assertEqual([record.source_row_number for record in records], [3])

    def test_load_company_products_maps_spu_columns(self) -> None:
        path = self._save_workbook(
            [
                [
                    "SPUID",
                    "SPU名称（可修改）",
                    "SPU基本单位",
                    "SPU别名（可修改）",
                    "SPU描述（可修改）",
                    "一级分类名称",
                    "二级分类名称",
                    "三级分类名称",
                ],
                ["C33882536", "海天金标生抽500ml", "瓶", "金标生抽", "500ml", "干调类", "调味品", "酱油"],
            ]
        )

        products = load_company_products(path)

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].product_id, "C33882536")
        self.assertEqual(products[0].code, "C33882536")
        self.assertEqual(products[0].name, "海天金标生抽500ml")
        self.assertEqual(products[0].unit, "瓶")
        self.assertEqual(products[0].alias, "金标生抽")
        self.assertEqual(products[0].description, "500ml")
        self.assertEqual(products[0].category_path, ["干调类", "调味品", "酱油"])
        self.assertEqual(products[0].raw_fields["SPUID"], "C33882536")


if __name__ == "__main__":
    unittest.main()
