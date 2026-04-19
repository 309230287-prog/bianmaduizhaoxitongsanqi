import json
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.model_trial import (
    ModelTrialCase,
    run_trial_cases,
    summarize_trial_results,
    write_trial_results_xlsx,
)


class ModelTrialTests(unittest.TestCase):
    def _case(self) -> ModelTrialCase:
        return ModelTrialCase(
            sample_id="GS0001",
            sample_group="strong_auto",
            expected_company_code="C33870472",
            expected_result_status="strong_auto_code",
            payload={
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "product": {
                            "code": "C33870472",
                            "name": "海天酱油金标生抽1*1.9L",
                        },
                    }
                ]
            },
        )

    def test_run_trial_cases_records_valid_model_decision(self) -> None:
        def call_model(_payload):
            return {
                "customer_semantic_summary": "海天金标生抽，1.9L瓶装。",
                "key_identity_signals": ["海天", "金标", "生抽", "1.9L", "瓶"],
                "strong_constraints": ["海天", "生抽", "1.9L", "瓶"],
                "weak_constraints": ["金标"],
                "ignored_or_noise_signals": [],
                "missing_or_uncertain_signals": [],
                "candidate_assessments": [
                    {
                        "candidate_id": "K000001",
                        "same_business_identity": True,
                        "matched_evidence": ["品牌、品名、规格、单位一致"],
                        "conflicts": [],
                        "missing_evidence": [],
                        "risk_flags": [],
                        "summary": "同一业务商品身份。",
                    }
                ],
                "selected_candidate_id": "K000001",
                "result_status": "strong_auto_code",
                "risk_flags": [],
                "evidence_summary": "证据完整一致。",
                "manual_review_reason": "",
                "can_auto_code": True,
            }

        results = run_trial_cases([self._case()], call_model)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].parse_ok)
        self.assertTrue(results[0].status_matches_expected)
        self.assertEqual(results[0].selected_company_code, "C33870472")
        self.assertTrue(results[0].selected_code_matches_expected)

    def test_run_trial_cases_records_invalid_json_without_crashing(self) -> None:
        def call_model(_payload):
            return "不是 JSON"

        results = run_trial_cases([self._case()], call_model)

        self.assertEqual(results[0].parsed_result_status, "model_error")
        self.assertFalse(results[0].parse_ok)
        self.assertIn("无法解析", results[0].manual_review_reason)

    def test_run_trial_cases_records_call_error_without_crashing(self) -> None:
        def call_model(_payload):
            raise RuntimeError("网络失败")

        results = run_trial_cases([self._case()], call_model)

        self.assertEqual(results[0].parsed_result_status, "model_error")
        self.assertFalse(results[0].parse_ok)
        self.assertIn("网络失败", results[0].error_message)

    def test_write_trial_results_xlsx(self) -> None:
        def call_model(_payload):
            return json.dumps(
                {
                    "customer_semantic_summary": "客户信息不足。",
                    "candidate_assessments": [],
                    "selected_candidate_id": None,
                    "result_status": "manual_review",
                    "risk_flags": ["insufficient_customer_info"],
                    "evidence_summary": "缺少规格。",
                    "manual_review_reason": "缺少规格，需要人工审核。",
                    "can_auto_code": False,
                },
                ensure_ascii=False,
            )

        results = run_trial_cases([self._case()], call_model)
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "model_trial_results.xlsx"
            write_trial_results_xlsx(results, output_path)

            workbook = load_workbook(output_path, read_only=True)
            worksheet = workbook["model_trial_results"]
            headers = [cell.value for cell in worksheet[1]]
            values = [cell.value for cell in worksheet[2]]
            workbook.close()

        self.assertIn("sample_id", headers)
        self.assertIn("raw_model_output", headers)
        self.assertIn("selected_code_matches_expected", headers)
        self.assertEqual(values[headers.index("sample_id")], "GS0001")
        self.assertEqual(values[headers.index("parsed_result_status")], "manual_review")

    def test_summarize_trial_results_counts_json_status_and_selected_code_matches(self) -> None:
        def call_model(payload):
            code = payload["candidate_products"][0]["product"]["code"]
            return {
                "customer_semantic_summary": "按样本选择候选。",
                "candidate_assessments": [
                    {
                        "candidate_id": "K000001",
                        "same_business_identity": True,
                        "risk_flags": [],
                        "summary": "候选可解释客户商品。",
                    }
                ],
                "selected_candidate_id": "K000001",
                "result_status": "strong_auto_code",
                "risk_flags": [],
                "evidence_summary": f"选择 {code}。",
                "manual_review_reason": "",
                "can_auto_code": True,
            }

        summary = summarize_trial_results(run_trial_cases([self._case()], call_model))

        self.assertEqual(summary["total_count"], 1)
        self.assertEqual(summary["json_valid_count"], 1)
        self.assertEqual(summary["status_match_count"], 1)
        self.assertEqual(summary["selected_code_match_count"], 1)
        self.assertEqual(summary["selected_code_mismatch_count"], 0)


if __name__ == "__main__":
    unittest.main()
