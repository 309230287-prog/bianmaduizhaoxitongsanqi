import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.candidate_generation import generate_candidates
from product_matcher_phase2.schemas import CompanyProduct, CustomerRecord


class CandidateGenerationTests(unittest.TestCase):
    def _product(
        self,
        code: str,
        name: str,
        unit: str,
        description: str = "",
    ) -> CompanyProduct:
        return CompanyProduct(
            product_id=code,
            code=code,
            name=name,
            unit=unit,
            alias="",
            description=description,
            category_path=[],
            raw_fields={},
        )

    def test_name_containment_creates_candidate_without_final_judgement(self) -> None:
        record = CustomerRecord(
            record_id="customer:1545",
            source_row_number=1545,
            raw_fields={},
            mapped_fields={"name": "海天金标生抽", "spec": "1*12*500ml", "unit": "件"},
        )
        products = [
            self._product("C33882536", "海天金标生抽500ml", "瓶", "500ml"),
            self._product("C00000001", "李锦记金标生抽500ml", "瓶", "500ml"),
        ]

        candidates = generate_candidates(record, products, limit=5)

        self.assertEqual(candidates[0].product.code, "C33882536")
        self.assertIn("name_contains", candidates[0].candidate_sources)
        self.assertIn("spec_in_product_text", candidates[0].candidate_sources)
        self.assertIn("单位不一致", candidates[0].candidate_notes)

    def test_exact_spec_and_unit_rank_before_name_only_match(self) -> None:
        record = CustomerRecord(
            record_id="customer:944",
            source_row_number=944,
            raw_fields={},
            mapped_fields={"name": "海天草菇老抽", "spec": "500ml", "unit": "瓶"},
        )
        products = [
            self._product("C33870454", "海天草菇老抽1.9L", "瓶", "1.9L"),
            self._product("C33882529", "海天草菇老抽500ml", "瓶", "500ml"),
        ]

        candidates = generate_candidates(record, products, limit=2)

        self.assertEqual([candidate.product.code for candidate in candidates], ["C33882529", "C33870454"])
        self.assertIn("unit_match", candidates[0].candidate_sources)

    def test_inserted_generic_word_does_not_hide_valid_candidate(self) -> None:
        record = CustomerRecord(
            record_id="customer:952",
            source_row_number=952,
            raw_fields={},
            mapped_fields={"name": "海天金标生抽", "spec": "1*1.9L", "unit": "瓶"},
        )
        products = [
            self._product("C33870472", "海天酱油金标生抽1*1.9L", "瓶", "1*1.9L"),
            self._product("C36476872", "海天金标生抽", "瓶", "1.6L"),
        ]

        candidates = generate_candidates(record, products, limit=2)

        self.assertEqual(candidates[0].product.code, "C33870472")
        self.assertIn("name_terms_match", candidates[0].candidate_sources)
        self.assertIn("spec_in_product_text", candidates[0].candidate_sources)

    def test_candidate_evidence_exposes_name_spec_unit_and_conflicts(self) -> None:
        record = CustomerRecord(
            record_id="customer:953",
            source_row_number=953,
            raw_fields={},
            mapped_fields={"name": "海天金标生抽", "spec": "1*6*1.9L", "unit": "件"},
        )
        products = [
            self._product("C33884118", "海天酱油金标生抽1*6*1.9L", "件", ""),
            self._product("C33870472", "海天酱油金标生抽1*1.9L", "瓶", ""),
        ]

        candidates = generate_candidates(record, products, limit=2)

        self.assertEqual(candidates[0].candidate_evidence.name_terms, ["金标", "生抽", "海天"])
        self.assertIn("1*6*1.9l", candidates[0].candidate_evidence.spec_tokens)
        self.assertIn("1.9l", candidates[0].candidate_evidence.spec_tokens)
        self.assertEqual(candidates[0].candidate_evidence.unit, "件")
        self.assertIn("spec_in_product_text", candidates[0].candidate_evidence.match_sources)
        self.assertEqual(candidates[0].candidate_evidence.conflict_notes, [])
        self.assertIn("单位不一致", candidates[1].candidate_evidence.conflict_notes[0])

    def test_spec_in_company_name_ranks_before_bare_exact_name_when_customer_has_spec(self) -> None:
        record = CustomerRecord(
            record_id="customer:1510",
            source_row_number=1510,
            raw_fields={},
            mapped_fields={"name": "海天草菇老抽", "spec": "[1*6*1.9L]", "unit": "件"},
        )
        products = [
            self._product("C35082079", "海天草菇老抽", "件", "1*6*1.9L"),
            self._product("C33870454", "海天草菇老抽1*6*1.9L-CC154369", "件", "1*6*1.9L"),
        ]

        candidates = generate_candidates(record, products, limit=2)

        self.assertEqual([candidate.product.code for candidate in candidates], ["C33870454", "C35082079"])
        self.assertIn("spec_in_product_name", candidates[0].candidate_sources)

    def test_business_synonym_terms_recall_vegetable_candidate(self) -> None:
        record = CustomerRecord(
            record_id="customer:444",
            source_row_number=444,
            raw_fields={},
            mapped_fields={"name": "优质粉西红柿", "unit": "斤", "category": "蔬菜类"},
        )
        products = [
            self._product("C33870314", "番茄（西红柿）抄码", "斤", "抄码"),
            self._product("C33870459", "海天番茄沙司1*510g", "瓶", "1*510g"),
        ]

        candidates = generate_candidates(record, products, limit=5)

        self.assertEqual(candidates[0].product.code, "C33870314")
        self.assertIn("name_terms_match", candidates[0].candidate_sources)

    def test_descriptive_prefix_does_not_hide_core_egg_candidate(self) -> None:
        record = CustomerRecord(
            record_id="customer:4",
            source_row_number=4,
            raw_fields={},
            mapped_fields={"name": "生咸鸭蛋/个", "unit": "个", "category": "蛋类"},
        )
        products = [
            self._product("C33871685", "咸鸭蛋抄码", "个", "抄码"),
            self._product("C33877102", "红太阳咸蛋黄200g", "包", "200g"),
        ]

        candidates = generate_candidates(record, products, limit=5)

        self.assertEqual(candidates[0].product.code, "C33871685")
        self.assertIn("name_terms_match", candidates[0].candidate_sources)

    def test_limit_is_respected_and_candidates_are_deterministic(self) -> None:
        record = CustomerRecord(
            record_id="customer:1",
            source_row_number=1,
            raw_fields={},
            mapped_fields={"name": "可口可乐", "spec": "330ml", "unit": "罐"},
        )
        products = [
            self._product("C2", "可口可乐330ml", "罐", "330ml"),
            self._product("C1", "可口可乐330ml", "罐", "330ml"),
            self._product("C3", "可口可乐500ml", "瓶", "500ml"),
        ]

        candidates = generate_candidates(record, products, limit=2)

        self.assertEqual([candidate.product.code for candidate in candidates], ["C1", "C2"])


if __name__ == "__main__":
    unittest.main()
