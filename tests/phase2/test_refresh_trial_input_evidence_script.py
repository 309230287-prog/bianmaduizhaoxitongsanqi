import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.phase2_refresh_trial_input_evidence import refresh_trial_input_evidence  # noqa: E402


class Phase2RefreshTrialInputEvidenceScriptTests(unittest.TestCase):
    def test_refresh_adds_current_candidate_evidence_to_legacy_jsonl(self) -> None:
        legacy_row = {
            "sample_id": "GSX",
            "sample_group": "strong_auto",
            "expected_company_code": "C1",
            "expected_result_status": "strong_auto_code",
            "payload": {
                "customer_record": {
                    "record_id": "customer:1",
                    "source_row_number": 1,
                    "raw_fields": {},
                    "mapped_fields": {"name": "海天金标生抽", "spec": "1*6*1.9L", "unit": "件"},
                },
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "candidate_sources": ["name_terms_match", "spec_in_product_text", "unit_match"],
                        "candidate_notes": "",
                        "product": {
                            "product_id": "C1",
                            "code": "C1",
                            "name": "海天酱油金标生抽1*6*1.9L",
                            "unit": "件",
                            "description": "",
                            "alias": "",
                            "category_path": [],
                            "raw_fields": {},
                        },
                    }
                ],
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.jsonl"
            output_path = Path(temp_dir) / "output.jsonl"
            input_path.write_text(json.dumps(legacy_row, ensure_ascii=False) + "\n", encoding="utf-8")

            summary = refresh_trial_input_evidence(input_path, output_path)

            refreshed = json.loads(output_path.read_text(encoding="utf-8"))

        evidence = refreshed["payload"]["candidate_products"][0]["candidate_evidence"]
        self.assertEqual(summary, {"rows": 1, "candidates": 1})
        self.assertEqual(evidence["name_terms"], ["金标", "生抽", "海天"])
        self.assertIn("1*6*1.9l", evidence["spec_tokens"])
        self.assertEqual(evidence["unit"], "件")
        self.assertIn("spec_in_product_text", evidence["match_sources"])

    def test_refresh_reranks_candidates_with_current_candidate_generation_logic(self) -> None:
        legacy_row = {
            "sample_id": "GS0006",
            "sample_group": "equivalence",
            "expected_company_code": "C33870454",
            "expected_result_status": "weak_auto_code",
            "payload": {
                "customer_record": {
                    "record_id": "customer:1510",
                    "source_row_number": 1510,
                    "raw_fields": {},
                    "mapped_fields": {"name": "海天草菇老抽", "spec": "[1*6*1.9L]", "unit": "件"},
                },
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "candidate_sources": ["name_exact", "spec_in_product_text", "unit_match"],
                        "candidate_notes": "",
                        "product": {
                            "product_id": "C35082079",
                            "code": "C35082079",
                            "name": "海天草菇老抽",
                            "unit": "件",
                            "description": "1*6*1.9L",
                            "alias": "",
                            "category_path": [],
                            "raw_fields": {},
                        },
                    },
                    {
                        "candidate_id": "K000002",
                        "candidate_sources": ["name_contains", "spec_in_product_text", "unit_match"],
                        "candidate_notes": "",
                        "product": {
                            "product_id": "C33870454",
                            "code": "C33870454",
                            "name": "海天草菇老抽1*6*1.9L-CC154369",
                            "unit": "件",
                            "description": "1*6*1.9L",
                            "alias": "",
                            "category_path": [],
                            "raw_fields": {},
                        },
                    },
                ],
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.jsonl"
            output_path = Path(temp_dir) / "output.jsonl"
            input_path.write_text(json.dumps(legacy_row, ensure_ascii=False) + "\n", encoding="utf-8")

            refresh_trial_input_evidence(input_path, output_path)
            refreshed = json.loads(output_path.read_text(encoding="utf-8"))

        candidates = refreshed["payload"]["candidate_products"]
        self.assertEqual(candidates[0]["candidate_id"], "K000001")
        self.assertEqual(candidates[0]["product"]["code"], "C33870454")
        self.assertIn("spec_in_product_name", candidates[0]["candidate_evidence"]["match_sources"])


if __name__ == "__main__":
    unittest.main()
