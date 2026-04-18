import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.evaluation import CandidateCoverageCase, calculate_candidate_coverage
from product_matcher_phase2.schemas import CandidateItem, CompanyProduct


class CandidateCoverageTests(unittest.TestCase):
    def _candidate(self, code: str) -> CandidateItem:
        return CandidateItem(
            candidate_id=f"K-{code}",
            product=CompanyProduct(product_id=code, code=code, name=f"商品{code}"),
        )

    def test_calculates_topn_candidate_coverage(self) -> None:
        report = calculate_candidate_coverage(
            [
                CandidateCoverageCase("GS0001", "C1", [self._candidate("C1")]),
                CandidateCoverageCase("GS0002", "C3", [self._candidate("C1"), self._candidate("C3")]),
                CandidateCoverageCase("GS0003", "", [self._candidate("C9")]),
            ],
            top_n_values=[1, 2],
        )

        self.assertEqual(report.evaluated_count, 2)
        self.assertEqual(report.topn_hits[1], 1)
        self.assertEqual(report.topn_hits[2], 2)
        self.assertEqual(report.topn_coverage[1], 0.5)
        self.assertEqual(report.topn_coverage[2], 1.0)
        self.assertEqual(report.missed_cases, [])

    def test_records_missed_expected_product_at_largest_topn(self) -> None:
        report = calculate_candidate_coverage(
            [
                CandidateCoverageCase(
                    sample_id="GS0004",
                    expected_company_code="C9",
                    candidates=[self._candidate("C1"), self._candidate("C2")],
                )
            ],
            top_n_values=[1, 2],
        )

        self.assertEqual(report.topn_coverage[2], 0.0)
        self.assertEqual(report.missed_cases[0].sample_id, "GS0004")
        self.assertEqual(report.missed_cases[0].candidate_codes, ["C1", "C2"])


if __name__ == "__main__":
    unittest.main()
