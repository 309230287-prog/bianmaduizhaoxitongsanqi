import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher.models import NormalizedRecord
from product_matcher.services.matching import build_match_preview

SEA_TIAN = "海天"
LI_JIN_JI = "李锦记"
SOY = "酱油"
SHENG_CHOU = "生抽"
PRESERVE_FILM = "保鲜膜"
BOTTLE = "瓶"
SEASONING = "调味品"


def make_record(**overrides) -> NormalizedRecord:
    base = dict(
        source_type="company",
        row_no=2,
        source_code="001",
        source_name=f"{SEA_TIAN}{SHENG_CHOU}1.9L",
        source_brand="",
        source_spec="",
        source_unit="",
        source_category=SEASONING,
        cleaned_name=f"{SEA_TIAN}{SHENG_CHOU}1.9L",
        parsed_brand=SEA_TIAN,
        parsed_name=SHENG_CHOU,
        parsed_spec="1.9L",
        parsed_unit=BOTTLE,
        parsed_category=SEASONING,
        parse_notes="",
    )
    base.update(overrides)
    return NormalizedRecord(**base)


class MatchingTests(unittest.TestCase):
    def test_auto_match_for_close_record(self) -> None:
        customer = make_record(source_type="customer", row_no=10, source_name=f"{SEA_TIAN}{SHENG_CHOU}", cleaned_name=f"{SEA_TIAN}{SHENG_CHOU}", parsed_spec="1.9L")
        company = make_record()
        results = build_match_preview([customer], [company])
        self.assertEqual(results[0].match_status, "auto_matched")

    def test_brand_conflict_goes_to_manual_review(self) -> None:
        customer = make_record(source_type="customer", parsed_brand=SEA_TIAN)
        company = make_record(parsed_brand=LI_JIN_JI, source_name=f"{LI_JIN_JI}{SHENG_CHOU}")
        results = build_match_preview([customer], [company])
        self.assertEqual(results[0].match_status, "manual_review")
        self.assertEqual(results[0].candidates[0].status, "hard_conflict")

    def test_incomplete_info_does_not_auto_match(self) -> None:
        customer = make_record(
            source_type="customer",
            row_no=10,
            source_name=f"{SEA_TIAN}{SHENG_CHOU}",
            cleaned_name=f"{SEA_TIAN}{SHENG_CHOU}",
            parsed_spec="",
        )
        company = make_record()
        results = build_match_preview([customer], [company])
        self.assertEqual(results[0].match_status, "suggested")

    def test_missing_candidate_becomes_unmatched(self) -> None:
        customer = make_record(
            source_type="customer",
            parsed_brand="",
            parsed_name=SOY,
            parsed_spec="",
            parsed_unit="",
            parsed_category="",
        )
        company = make_record(
            parsed_brand="",
            source_name=PRESERVE_FILM,
            cleaned_name=PRESERVE_FILM,
            parsed_name=PRESERVE_FILM,
            parsed_spec="",
            parsed_unit="",
            parsed_category="",
        )
        results = build_match_preview([customer], [company])
        self.assertEqual(results[0].match_status, "unmatched")


if __name__ == "__main__":
    unittest.main()
