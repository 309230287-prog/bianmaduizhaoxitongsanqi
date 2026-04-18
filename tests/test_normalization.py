import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher.services import normalization
from product_matcher.services.normalization import clean_name, extract_brand, extract_product_name, extract_spec, extract_unit

SEA_TIAN = "海天"
LI_JIN_JI = "李锦记"
YAN_TANG = "燕塘"
COLA = "可口可乐"
SOY_SAUCE = "酱油"
JIN_BIAO_SHENG_CHOU = "金标生抽"
MAPPING_NOTE = "映射列"
DICT_NOTE = "词库"
BOTTLE = "瓶"


class NormalizationTests(unittest.TestCase):
    def test_clean_name_removes_supply_code(self) -> None:
        self.assertEqual(clean_name(f"{SEA_TIAN}{JIN_BIAO_SHENG_CHOU}1*1.9L-CC154882"), f"{SEA_TIAN}{JIN_BIAO_SHENG_CHOU}1*1.9L")

    def test_extract_spec_prefers_explicit_column(self) -> None:
        spec, note = extract_spec("1*500g", f"{SEA_TIAN}{JIN_BIAO_SHENG_CHOU}")
        self.assertEqual(spec, "1*500g")
        self.assertIn(MAPPING_NOTE, note)

    def test_extract_brand_uses_dictionary(self) -> None:
        brand, note = extract_brand("", f"{SEA_TIAN}{SOY_SAUCE}", {SEA_TIAN, LI_JIN_JI})
        self.assertEqual(brand, SEA_TIAN)
        self.assertIn(DICT_NOTE, note)

    def test_load_brand_dictionary_prefers_external_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dictionary_dir = tmp_path / "dictionaries"
            dictionary_dir.mkdir(parents=True, exist_ok=True)
            brand_file = dictionary_dir / "brands.txt"
            product_file = dictionary_dir / "product_keywords.txt"
            brand_file.write_text(f"{YAN_TANG}\n{COLA}\n", encoding="utf-8")
            product_file.write_text("", encoding="utf-8")

            with patch.object(normalization, "DICTIONARY_DIR", dictionary_dir),                  patch.object(normalization, "BRAND_DICTIONARY_FILE", brand_file),                  patch.object(normalization, "PRODUCT_KEYWORD_FILE", product_file):
                loaded = normalization.load_brand_dictionary({SEA_TIAN})

            self.assertEqual(loaded, {SEA_TIAN, YAN_TANG, COLA})

    def test_extract_product_name_removes_brand_and_spec(self) -> None:
        name, _ = extract_product_name(f"{SEA_TIAN}{SOY_SAUCE}{JIN_BIAO_SHENG_CHOU}1.9L", SEA_TIAN, "1.9L")
        self.assertEqual(name, f"{SOY_SAUCE}{JIN_BIAO_SHENG_CHOU}")

    def test_extract_product_name_uses_product_dictionary_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dictionary_dir = tmp_path / "dictionaries"
            dictionary_dir.mkdir(parents=True, exist_ok=True)
            brand_file = dictionary_dir / "brands.txt"
            product_file = dictionary_dir / "product_keywords.txt"
            brand_file.write_text("", encoding="utf-8")
            product_file.write_text("soy sauce|premium soy sauce|gold label soy sauce\n", encoding="utf-8")

            with patch.object(normalization, "DICTIONARY_DIR", dictionary_dir), \
                 patch.object(normalization, "BRAND_DICTIONARY_FILE", brand_file), \
                 patch.object(normalization, "PRODUCT_KEYWORD_FILE", product_file):
                product_dictionary = normalization.load_product_dictionary()

            name, note = extract_product_name("Brand premium soy sauce 500ml", "Brand", "500ml", product_dictionary)

        self.assertEqual(name, "soy sauce")
        self.assertIn(DICT_NOTE, note)

    def test_extract_unit_prefers_explicit_value(self) -> None:
        unit, note = extract_unit(BOTTLE, f"{SEA_TIAN}{SOY_SAUCE}", "500ml")
        self.assertEqual(unit, BOTTLE)
        self.assertIn(MAPPING_NOTE, note)


if __name__ == "__main__":
    unittest.main()
