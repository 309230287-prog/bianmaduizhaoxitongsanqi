import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher.services.excel_preview import WorkbookPreviewError, build_workbook_preview


class ExcelPreviewTests(unittest.TestCase):
    def test_build_preview_reads_headers_and_rows(self) -> None:
        content = self._make_workbook_bytes(
            ["商品名称", "编号", "规格"],
            [
                ["海天酱油", "001", "500ml"],
                ["李锦记蚝油", "002", "700g"],
            ],
        )

        preview = build_workbook_preview("sample.xlsx", content)

        self.assertEqual(preview.sheet_name, "Sheet")
        self.assertEqual(preview.total_rows, 2)
        self.assertEqual([column.raw_header for column in preview.columns], ["商品名称", "编号", "规格"])
        self.assertEqual(preview.sample_rows[0], ["海天酱油", "001", "500ml"])

    def test_blank_headers_are_labeled(self) -> None:
        content = self._make_workbook_bytes(
            [None, "商品名称", "商品名称"],
            [["", "海天酱油", "海天酱油"]],
        )

        preview = build_workbook_preview("sample.xlsx", content)

        self.assertEqual(preview.columns[0].raw_header, "空白列")
        self.assertIn("重复列", preview.columns[2].label)

    def test_non_xlsx_file_is_rejected(self) -> None:
        with self.assertRaises(WorkbookPreviewError):
            build_workbook_preview("sample.xls", b"not-a-real-workbook")

    def _make_workbook_bytes(self, header, rows) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(header)
        for row in rows:
            sheet.append(row)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            temp_path = Path(tmp.name)
        try:
            workbook.save(temp_path)
            return temp_path.read_bytes()
        finally:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()