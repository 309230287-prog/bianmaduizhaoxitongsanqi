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
        self.assertEqual(summary["unsafe_auto_code_count"], 0)

    def test_summarize_trial_results_counts_unsafe_auto_code(self) -> None:
        manual_case = ModelTrialCase(
            sample_id="GS0009",
            sample_group="manual_review",
            expected_company_code="",
            expected_result_status="manual_review",
            payload={
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "product": {
                            "code": "C000001",
                            "name": "候选商品",
                        },
                    }
                ]
            },
        )

        def call_model(_payload):
            return {
                "customer_semantic_summary": "错误地强行自动落码。",
                "candidate_assessments": [
                    {
                        "candidate_id": "K000001",
                        "same_business_identity": True,
                        "risk_flags": [],
                        "summary": "模型误判为可自动。",
                    }
                ],
                "selected_candidate_id": "K000001",
                "result_status": "strong_auto_code",
                "risk_flags": [],
                "evidence_summary": "证据不足仍自动。",
                "manual_review_reason": "",
                "can_auto_code": True,
            }

        summary = summarize_trial_results(run_trial_cases([manual_case], call_model))

        self.assertEqual(summary["auto_code_count"], 1)
        self.assertEqual(summary["unsafe_auto_code_count"], 1)

    def test_run_trial_cases_blocks_auto_code_when_customer_spec_has_no_candidate_spec_evidence(self) -> None:
        case = ModelTrialCase(
            sample_id="GS0029",
            sample_group="manual_or_unmatched",
            expected_company_code="C34256292",
            expected_result_status="suggested_code",
            payload={
                "customer_record": {
                    "mapped_fields": {"name": "白辣椒", "spec": "[1*500g]", "unit": "斤"}
                },
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "candidate_evidence": {"spec_tokens": [], "match_sources": ["name_exact", "unit_match"]},
                        "product": {"code": "C34256292", "name": "白辣椒"},
                    }
                ],
            },
        )

        def call_model(_payload):
            return {
                "customer_semantic_summary": "白辣椒，规格 1*500g，单位斤。",
                "candidate_assessments": [
                    {
                        "candidate_id": "K000001",
                        "same_business_identity": True,
                        "risk_flags": [],
                        "summary": "模型误认为可自动。",
                    }
                ],
                "selected_candidate_id": "K000001",
                "result_status": "strong_auto_code",
                "risk_flags": [],
                "evidence_summary": "模型忽略了候选缺少规格证据。",
                "manual_review_reason": "",
                "can_auto_code": True,
            }

        result = run_trial_cases([case], call_model)[0]

        self.assertEqual(result.parsed_result_status, "suggested_code")
        self.assertFalse(result.can_auto_code)
        self.assertTrue(result.selected_code_matches_expected)
        self.assertFalse(summarize_trial_results([result])["unsafe_auto_code_count"])
        self.assertIn("候选缺少与客户规格匹配的证据", result.manual_review_reason)

    def test_run_trial_cases_blocks_auto_code_when_selected_candidate_unit_conflicts(self) -> None:
        case = ModelTrialCase(
            sample_id="UNIT001",
            sample_group="manual_review",
            expected_company_code="C000001",
            expected_result_status="manual_review",
            payload={
                "customer_record": {"mapped_fields": {"name": "海天金标生抽", "unit": "件"}},
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "candidate_evidence": {"unit": "瓶", "match_sources": ["name_exact"]},
                        "product": {"code": "C000001", "name": "海天金标生抽", "unit": "瓶"},
                    }
                ],
            },
        )

        result = run_trial_cases([case], self._strong_auto_model)[0]

        self.assertEqual(result.parsed_result_status, "manual_review")
        self.assertFalse(result.can_auto_code)
        self.assertIn("单位冲突", result.manual_review_reason)

    def test_run_trial_cases_blocks_auto_code_when_package_spec_conflicts_despite_volume_overlap(self) -> None:
        case = ModelTrialCase(
            sample_id="SPEC001",
            sample_group="manual_review",
            expected_company_code="C000001",
            expected_result_status="manual_review",
            payload={
                "customer_record": {"mapped_fields": {"name": "海天金标生抽", "spec": "1*6*1.9L", "unit": "件"}},
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "candidate_evidence": {
                            "unit": "件",
                            "spec_tokens": ["1*1.9l", "1.9l"],
                            "match_sources": ["name_contains", "spec_in_product_text", "unit_match"],
                        },
                        "product": {"code": "C000001", "name": "海天金标生抽1*1.9L", "unit": "件"},
                    }
                ],
            },
        )

        result = run_trial_cases([case], self._strong_auto_model)[0]

        self.assertEqual(result.parsed_result_status, "manual_review")
        self.assertFalse(result.can_auto_code)
        self.assertIn("规格或包装层级不一致", result.manual_review_reason)

    def test_run_trial_cases_blocks_auto_code_when_multiple_candidates_have_same_identity_evidence(self) -> None:
        case = ModelTrialCase(
            sample_id="DUP001",
            sample_group="manual_review",
            expected_company_code="C000001",
            expected_result_status="manual_review",
            payload={
                "customer_record": {"mapped_fields": {"name": "海天金标生抽", "spec": "1*6*1.9L", "unit": "件"}},
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "candidate_evidence": {
                            "unit": "件",
                            "spec_tokens": ["1*6*1.9l", "1.9l"],
                            "match_sources": ["name_contains", "spec_in_product_text", "unit_match"],
                        },
                        "product": {"code": "C000001", "name": "海天金标生抽1*6*1.9L", "unit": "件"},
                    },
                    {
                        "candidate_id": "K000002",
                        "candidate_evidence": {
                            "unit": "件",
                            "spec_tokens": ["1*6*1.9l", "1.9l"],
                            "match_sources": ["name_contains", "spec_in_product_text", "unit_match"],
                        },
                        "product": {"code": "C000002", "name": "海天金标生抽1*6*1.9L-副本", "unit": "件"},
                    },
                ],
            },
        )

        result = run_trial_cases([case], self._strong_auto_model)[0]

        self.assertEqual(result.parsed_result_status, "manual_review")
        self.assertFalse(result.can_auto_code)
        self.assertIn("多个候选", result.manual_review_reason)

    def test_run_trial_cases_adds_top_candidate_suggestion_for_manual_review_without_auto_code(self) -> None:
        case = ModelTrialCase(
            sample_id="SUG001",
            sample_group="manual_review",
            expected_company_code="C000001",
            expected_result_status="manual_review",
            payload={
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "candidate_evidence": {"match_sources": ["name_exact"]},
                        "product": {"code": "C000001", "name": "建议候选"},
                    }
                ],
            },
        )

        def call_model(_payload):
            return {
                "customer_semantic_summary": "需要人工审核。",
                "candidate_assessments": [],
                "selected_candidate_id": None,
                "result_status": "manual_review",
                "risk_flags": ["insufficient_customer_info"],
                "evidence_summary": "模型未选择候选。",
                "manual_review_reason": "需要人工确认。",
                "can_auto_code": False,
            }

        result = run_trial_cases([case], call_model)[0]

        self.assertEqual(result.parsed_result_status, "manual_review")
        self.assertEqual(result.selected_candidate_id, "K000001")
        self.assertEqual(result.selected_company_code, "C000001")
        self.assertFalse(result.can_auto_code)

    def test_bracketed_customer_spec_can_downgrade_strong_auto_to_weak_auto_when_top_candidate_is_explicit(self) -> None:
        case = ModelTrialCase(
            sample_id="WEAK001",
            sample_group="equivalence",
            expected_company_code="C000001",
            expected_result_status="weak_auto_code",
            payload={
                "customer_record": {"mapped_fields": {"name": "海天草菇老抽", "spec": "[1*6*1.9L]", "unit": "件"}},
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "candidate_evidence": {
                            "unit": "件",
                            "spec_tokens": ["1*6*1.9l", "1.9l"],
                            "match_sources": ["name_contains", "spec_in_product_text", "spec_in_product_name", "unit_match"],
                        },
                        "product": {"code": "C000001", "name": "海天草菇老抽1*6*1.9L", "unit": "件"},
                    },
                    {
                        "candidate_id": "K000002",
                        "candidate_evidence": {
                            "unit": "件",
                            "spec_tokens": ["1*6*1.9l", "1.9l"],
                            "match_sources": ["name_exact", "spec_in_product_text", "unit_match"],
                        },
                        "product": {"code": "C000002", "name": "海天草菇老抽", "unit": "件"},
                    },
                ],
            },
        )

        result = run_trial_cases([case], self._strong_auto_model)[0]

        self.assertEqual(result.parsed_result_status, "weak_auto_code")
        self.assertTrue(result.can_auto_code)
        self.assertEqual(result.selected_company_code, "C000001")
        self.assertEqual(summarize_trial_results([result])["unsafe_auto_code_count"], 0)

    def test_manual_review_with_single_top_hint_becomes_suggested_code_without_auto_code(self) -> None:
        case = ModelTrialCase(
            sample_id="SUG002",
            sample_group="hidden_info",
            expected_company_code="C000001",
            expected_result_status="suggested_code",
            payload={
                "customer_record": {"mapped_fields": {"name": "广祥泰鸡饭老抽640ml", "unit": "瓶"}},
                "candidate_products": [
                    {
                        "candidate_id": "K000001",
                        "candidate_evidence": {
                            "unit": "瓶",
                            "spec_tokens": ["1*640ml", "640ml"],
                            "match_sources": ["name_terms_match", "unit_match"],
                            "conflict_notes": [],
                        },
                        "product": {"code": "C000001", "name": "广泰祥鸡饭老抽1*640ml", "unit": "瓶"},
                    },
                    {
                        "candidate_id": "K000002",
                        "candidate_evidence": {
                            "unit": "瓶",
                            "spec_tokens": ["1*1.9l", "1.9l"],
                            "match_sources": ["name_terms_match", "unit_match"],
                            "conflict_notes": [],
                        },
                        "product": {"code": "C000002", "name": "海天老抽1*1.9L", "unit": "瓶"},
                    },
                ],
            },
        )

        def call_model(_payload):
            return {
                "customer_semantic_summary": "存在品牌字序风险。",
                "candidate_assessments": [],
                "selected_candidate_id": None,
                "result_status": "manual_review",
                "risk_flags": ["brand_conflict"],
                "evidence_summary": "首候选可作为建议。",
                "manual_review_reason": "品牌字序需人工确认。",
                "can_auto_code": False,
            }

        result = run_trial_cases([case], call_model)[0]

        self.assertEqual(result.parsed_result_status, "suggested_code")
        self.assertEqual(result.selected_company_code, "C000001")
        self.assertFalse(result.can_auto_code)

    def _strong_auto_model(self, _payload):
        return {
            "customer_semantic_summary": "模型认为可自动。",
            "candidate_assessments": [
                {
                    "candidate_id": "K000001",
                    "same_business_identity": True,
                    "risk_flags": [],
                    "summary": "模型误认为可自动。",
                }
            ],
            "selected_candidate_id": "K000001",
            "result_status": "strong_auto_code",
            "risk_flags": [],
            "evidence_summary": "模型判断可自动。",
            "manual_review_reason": "",
            "can_auto_code": True,
        }


if __name__ == "__main__":
    unittest.main()
