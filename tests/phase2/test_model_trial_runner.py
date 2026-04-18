import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.model_trial_runner import (
    build_chat_json_model_caller,
    run_trial_from_files,
)


class ModelTrialRunnerTests(unittest.TestCase):
    def _trial_input_path(self, directory: Path) -> Path:
        path = directory / "trial_inputs.jsonl"
        row = {
            "sample_id": "GS0001",
            "sample_group": "strong_auto",
            "expected_company_code": "",
            "expected_result_status": "manual_review",
            "payload": {"customer_record": {"record_id": "C1"}, "candidate_products": []},
        }
        path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def test_build_chat_json_model_caller_passes_phase2_prompt_and_payload(self) -> None:
        calls = []

        def fake_chat_json(runtime_settings, system_prompt, user_payload, *, temperature, max_tokens):
            calls.append(
                {
                    "runtime_settings": runtime_settings,
                    "system_prompt": system_prompt,
                    "user_payload": user_payload,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )
            return {
                "customer_semantic_summary": "缺少候选。",
                "candidate_assessments": [],
                "selected_candidate_id": None,
                "result_status": "manual_review",
                "risk_flags": ["candidate_pool_missing_evidence"],
                "evidence_summary": "无候选。",
                "manual_review_reason": "候选池为空，需要人工审核。",
                "can_auto_code": False,
            }

        caller = build_chat_json_model_caller(
            runtime_settings={"production_model_name": "test-model"},
            chat_json_func=fake_chat_json,
        )

        response = caller({"hello": "world"})

        self.assertEqual(response["result_status"], "manual_review")
        self.assertIn("商品编码对照系统二期", calls[0]["system_prompt"])
        self.assertEqual(calls[0]["user_payload"], {"hello": "world"})
        self.assertEqual(calls[0]["temperature"], 0.0)
        self.assertGreaterEqual(calls[0]["max_tokens"], 2000)

    def test_run_trial_from_files_writes_results_and_returns_summary(self) -> None:
        def fake_model_caller(_payload):
            return {
                "customer_semantic_summary": "缺少候选。",
                "candidate_assessments": [],
                "selected_candidate_id": None,
                "result_status": "manual_review",
                "risk_flags": ["candidate_pool_missing_evidence"],
                "evidence_summary": "无候选。",
                "manual_review_reason": "候选池为空，需要人工审核。",
                "can_auto_code": False,
            }

        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path = self._trial_input_path(directory)
            output_path = directory / "trial_results.xlsx"

            summary = run_trial_from_files(input_path, output_path, fake_model_caller)

            self.assertTrue(output_path.exists())
            self.assertEqual(summary["total_count"], 1)
            self.assertEqual(summary["json_valid_count"], 1)
            self.assertEqual(summary["status_match_count"], 1)

    def test_run_trial_from_files_can_limit_trial_case_count(self) -> None:
        calls = []

        def fake_model_caller(payload):
            calls.append(payload)
            return {
                "customer_semantic_summary": "缺少候选。",
                "candidate_assessments": [],
                "selected_candidate_id": None,
                "result_status": "manual_review",
                "risk_flags": ["candidate_pool_missing_evidence"],
                "evidence_summary": "无候选。",
                "manual_review_reason": "候选池为空，需要人工审核。",
                "can_auto_code": False,
            }

        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path = directory / "trial_inputs.jsonl"
            rows = [
                {
                    "sample_id": f"GS000{i}",
                    "sample_group": "manual_review",
                    "expected_company_code": "",
                    "expected_result_status": "manual_review",
                    "payload": {"customer_record": {"record_id": f"C{i}"}, "candidate_products": []},
                }
                for i in range(1, 4)
            ]
            input_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )
            output_path = directory / "trial_results.xlsx"

            summary = run_trial_from_files(input_path, output_path, fake_model_caller, limit=2)

            self.assertEqual(summary["total_count"], 2)
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0]["customer_record"]["record_id"], "C1")
            self.assertEqual(calls[1]["customer_record"]["record_id"], "C2")


if __name__ == "__main__":
    unittest.main()
