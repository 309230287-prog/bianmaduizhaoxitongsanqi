import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2_run_model_trial import parse_args  # noqa: E402


class Phase2RunModelTrialScriptTests(unittest.TestCase):
    def test_parse_args_accepts_optional_limit(self) -> None:
        args = parse_args(["--limit", "10"])

        self.assertEqual(args.limit, 10)

    def test_parse_args_leaves_limit_unset_by_default(self) -> None:
        args = parse_args([])

        self.assertIsNone(args.limit)


if __name__ == "__main__":
    unittest.main()
