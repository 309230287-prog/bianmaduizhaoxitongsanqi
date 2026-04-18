import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.candidate_pool import generate_candidates
from product_matcher_phase2.schemas import CompanyProduct, CustomerRecord


class CandidatePoolEntryPointTests(unittest.TestCase):
    def test_candidate_pool_exposes_generate_candidates(self) -> None:
        record = CustomerRecord(
            record_id="customer:1",
            source_row_number=1,
            raw_fields={},
            mapped_fields={"name": "海天金标生抽", "spec": "500ml", "unit": "瓶"},
        )
        products = [
            CompanyProduct(
                product_id="C1",
                code="C1",
                name="海天金标生抽500ml",
                unit="瓶",
                description="500ml",
            )
        ]

        candidates = generate_candidates(record, products, limit=10)

        self.assertEqual(candidates[0].product.code, "C1")


if __name__ == "__main__":
    unittest.main()
