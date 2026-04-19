import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2_run_batch import parse_args  # noqa: E402


class Phase2RunBatchScriptTests(unittest.TestCase):
    def test_parse_args_defaults_to_project_excel_files(self) -> None:
        args = parse_args([])

        self.assertTrue(args.customer.endswith("客户商品库.xlsx"))
        self.assertTrue(args.company.endswith("我司商品库.xlsx"))
        self.assertTrue(args.output.endswith("phase2_batch_results.xlsx"))

    def test_parse_args_accepts_limit_and_candidate_limit(self) -> None:
        args = parse_args(["--limit", "5", "--candidate-limit", "7"])

        self.assertEqual(args.limit, 5)
        self.assertEqual(args.candidate_limit, 7)


if __name__ == "__main__":
    unittest.main()
