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

from product_matcher_phase2.batch_runner import (
    build_phase2_batch_cases,
    run_phase2_batch,
    summarize_batch_results,
    write_phase2_batch_results_xlsx,
)
from product_matcher_phase2.schemas import CompanyProduct, CustomerRecord


class Phase2BatchRunnerTests(unittest.TestCase):
    def _customer(self) -> CustomerRecord:
        return CustomerRecord(
            record_id="customer:2",
            source_row_number=2,
            raw_fields={"商品名称": "海天金标生抽", "规格": "500ml", "单位": "瓶"},
            mapped_fields={"name": "海天金标生抽", "spec": "500ml", "unit": "瓶"},
        )

    def _products(self) -> list[CompanyProduct]:
        return [
            CompanyProduct(
                product_id="C33882536",
                code="C33882536",
                name="海天金标生抽500ml",
                unit="瓶",
                raw_fields={"内部成本": "不要发给模型"},
            ),
            CompanyProduct(
                product_id="C00000001",
                code="C00000001",
                name="海天金标生抽1.9L",
                unit="瓶",
            ),
        ]

    def test_build_phase2_batch_cases_generates_compact_model_payloads(self) -> None:
        cases = build_phase2_batch_cases([self._customer()], self._products(), candidate_limit=1)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].sample_id, "customer:2")
        self.assertEqual(cases[0].sample_group, "live_batch")
        self.assertEqual(cases[0].expected_company_code, "")
        candidates = cases[0].payload["candidate_products"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["product"]["code"], "C33882536")
        self.assertNotIn("raw_fields", candidates[0]["product"])

    def test_run_phase2_batch_keeps_customer_and_selected_product_context(self) -> None:
        def call_model(_payload):
            return {
                "customer_semantic_summary": "海天金标生抽，500ml，瓶。",
                "candidate_assessments": [
                    {
                        "candidate_id": "K000001",
                        "same_business_identity": True,
                        "risk_flags": [],
                        "summary": "名称、规格、单位一致。",
                    }
                ],
                "selected_candidate_id": "K000001",
                "result_status": "strong_auto_code",
                "risk_flags": [],
                "evidence_summary": "名称、规格、单位一致。",
                "manual_review_reason": "",
                "can_auto_code": True,
            }

        rows = run_phase2_batch([self._customer()], self._products(), call_model, candidate_limit=1)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].customer_record.source_row_number, 2)
        self.assertEqual(rows[0].result.selected_company_code, "C33882536")
        self.assertEqual(rows[0].selected_product_name, "海天金标生抽500ml")
        self.assertTrue(rows[0].result.can_auto_code)

    def test_write_phase2_batch_results_xlsx_exports_review_columns(self) -> None:
        def call_model(_payload):
            return json.dumps(
                {
                    "customer_semantic_summary": "海天金标生抽，500ml，瓶。",
                    "candidate_assessments": [],
                    "selected_candidate_id": "K000001",
                    "result_status": "suggested_code",
                    "risk_flags": ["multiple_valid_candidates"],
                    "evidence_summary": "可建议，但需要人工确认。",
                    "manual_review_reason": "存在多个相似候选。",
                    "can_auto_code": False,
                },
                ensure_ascii=False,
            )

        rows = run_phase2_batch([self._customer()], self._products(), call_model, candidate_limit=1)
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "phase2_batch.xlsx"
            write_phase2_batch_results_xlsx(rows, output_path)

            workbook = load_workbook(output_path, read_only=True)
            worksheet = workbook["phase2_batch_results"]
            headers = [cell.value for cell in worksheet[1]]
            values = [cell.value for cell in worksheet[2]]
            workbook.close()

        self.assertIn("客户行号", headers)
        self.assertIn("二期判断状态", headers)
        self.assertIn("是否自动落码", headers)
        self.assertIn("建议我司编码", headers)
        self.assertIn("建议我司商品名称", headers)
        self.assertIn("证据说明", headers)
        self.assertEqual(values[headers.index("客户行号")], 2)
        self.assertEqual(values[headers.index("二期判断状态")], "suggested_code")
        self.assertEqual(values[headers.index("建议我司编码")], "C33882536")
        self.assertEqual(values[headers.index("建议我司商品名称")], "海天金标生抽500ml")

    def test_summarize_batch_results_counts_live_batch_without_golden_expectations(self) -> None:
        def call_model(_payload):
            return {
                "customer_semantic_summary": "无候选。",
                "candidate_assessments": [],
                "selected_candidate_id": None,
                "result_status": "unmatched",
                "risk_flags": ["candidate_pool_missing_evidence"],
                "evidence_summary": "未找到候选。",
                "manual_review_reason": "候选池为空。",
                "can_auto_code": False,
            }

        rows = run_phase2_batch([self._customer()], [], call_model)

        summary = summarize_batch_results(rows)

        self.assertEqual(summary["total_count"], 1)
        self.assertEqual(summary["json_valid_count"], 1)
        self.assertEqual(summary["auto_code_count"], 0)
        self.assertEqual(summary["suggested_or_review_count"], 0)
        self.assertEqual(summary["unmatched_count"], 1)


if __name__ == "__main__":
    unittest.main()
