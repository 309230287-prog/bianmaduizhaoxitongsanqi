import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher.models import ColumnOption, WorkbookPreview
from product_matcher.services import storage


class StorageTemplateTests(unittest.TestCase):
    def test_save_and_load_mapping_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            template_file = Path(tmp_dir) / 'mapping_templates.json'
            company_preview = WorkbookPreview(
                filename='company.xlsx',
                sheet_name='Sheet1',
                total_rows=2,
                columns=[
                    ColumnOption(1, 'SPUID', 'SPUID', 'col_1'),
                    ColumnOption(2, 'SPU名称', 'SPU名称', 'col_2'),
                ],
                sample_rows=[],
            )
            customer_preview = WorkbookPreview(
                filename='customer.xlsx',
                sheet_name='Sheet1',
                total_rows=2,
                columns=[
                    ColumnOption(1, '商品名称', '商品名称', 'col_1'),
                    ColumnOption(2, '编号', '编号', 'col_2'),
                ],
                sample_rows=[],
            )
            company_mapping = {'product_code': 'col_1', 'product_name': 'col_2'}
            customer_mapping = {'product_code': 'col_2', 'product_name': 'col_1'}

            with patch.object(storage, 'TEMPLATE_FILE', template_file):
                storage.save_mapping_template(company_preview, customer_preview, company_mapping, customer_mapping)
                loaded = storage.load_mapping_template(company_preview, customer_preview)

            self.assertEqual(loaded, (company_mapping, customer_mapping))
            payload = json.loads(template_file.read_text(encoding='utf-8'))
            self.assertEqual(len(payload), 1)

    def test_different_signature_does_not_reuse_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            template_file = Path(tmp_dir) / 'mapping_templates.json'
            preview_a = WorkbookPreview(
                filename='a.xlsx',
                sheet_name='Sheet1',
                total_rows=1,
                columns=[ColumnOption(1, '商品名称', '商品名称', 'col_1')],
                sample_rows=[],
            )
            preview_b = WorkbookPreview(
                filename='b.xlsx',
                sheet_name='Sheet1',
                total_rows=1,
                columns=[ColumnOption(1, '产品名称', '产品名称', 'col_1')],
                sample_rows=[],
            )

            with patch.object(storage, 'TEMPLATE_FILE', template_file):
                storage.save_mapping_template(preview_a, preview_a, {'product_name': 'col_1'}, {'product_name': 'col_1'})
                loaded = storage.load_mapping_template(preview_b, preview_b)

            self.assertIsNone(loaded)


if __name__ == '__main__':
    unittest.main()
