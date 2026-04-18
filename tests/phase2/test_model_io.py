import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.memory import MemoryScope, MemoryStatus, MemoryType, ProductMemoryItem
from product_matcher_phase2.model_io import (
    build_model_input_payload,
    parse_model_decision_response,
    render_model_prompt,
)
from product_matcher_phase2.schemas import CandidateItem, CompanyProduct, CustomerRecord


class ModelInputPayloadTests(unittest.TestCase):
    def _record(self) -> CustomerRecord:
        return CustomerRecord(
            record_id="C000001",
            source_row_number=1545,
            raw_fields={
                "商品名称": "海天金标生抽",
                "规格": "[1*12*500ml]",
                "单位": "件",
                "备注": "客户原表备注不能丢",
            },
            mapped_fields={
                "name": "海天金标生抽",
                "spec": "1*12*500ml",
                "unit": "件",
                "remark": "客户原表备注不能丢",
            },
        )

    def _candidate(self) -> CandidateItem:
        return CandidateItem(
            candidate_id="K000001",
            product=CompanyProduct(
                product_id="P33882536",
                code="C33882536",
                name="海天金标生抽500ml",
                unit="瓶",
                alias="",
                description="500ml",
                category_path=["干调类", "调味品", "酱油"],
                raw_fields={"商品编码": "C33882536", "商品名称": "海天金标生抽500ml"},
            ),
            candidate_sources=["name_search", "brand_match", "spec_partial_match"],
            candidate_notes="客户是整件规格，候选是单瓶规格，需要模型识别包装层级风险。",
        )

    def _memory(self) -> ProductMemoryItem:
        return ProductMemoryItem(
            memory_id="M000001",
            memory_type=MemoryType.MANUAL_CONFIRMATION,
            scope=MemoryScope.CUSTOMER_SPECIFIC,
            customer_id="客户A",
            source_text="1*12*500ml",
            normalized_meaning="该客户这里表达一件十二瓶五百毫升。",
            company_product_id="P33882536",
            applicable_conditions={"name": "海天金标生抽", "unit": "件"},
            confidence_level="confirmed",
            can_support_weak_auto_code=True,
            created_from_record_id="C000900",
            created_by="人工审核",
            status=MemoryStatus.ACTIVE,
        )

    def test_payload_preserves_customer_candidate_and_memory_evidence(self) -> None:
        payload = build_model_input_payload(
            record=self._record(),
            candidates=[self._candidate()],
            applicable_memories=[self._memory()],
        )

        self.assertEqual(payload["customer_record"]["raw_fields"]["备注"], "客户原表备注不能丢")
        self.assertEqual(payload["customer_record"]["mapped_fields"]["spec"], "1*12*500ml")
        self.assertEqual(
            payload["candidate_products"][0]["product"]["raw_fields"]["商品编码"],
            "C33882536",
        )
        self.assertIn("spec_partial_match", payload["candidate_products"][0]["candidate_sources"])
        self.assertEqual(payload["applicable_memories"][0]["memory_id"], "M000001")

    def test_payload_contains_phase2_guardrail_rules(self) -> None:
        payload = build_model_input_payload(
            record=self._record(),
            candidates=[self._candidate()],
            applicable_memories=[],
        )

        rules = "\n".join(payload["judgement_rules"])

        self.assertIn("不要脑补", rules)
        self.assertIn("不能只按名称相似", rules)
        self.assertIn("规格", rules)
        self.assertIn("人工审核", rules)

    def test_payload_mentions_allowed_risk_flag_enum_values(self) -> None:
        payload = build_model_input_payload(
            record=self._record(),
            candidates=[self._candidate()],
            applicable_memories=[],
        )

        required_output_format = payload["required_output_format"]
        self.assertIn("brand_conflict", required_output_format["candidate_assessments"][0]["risk_flags"])
        self.assertIn("multiple_valid_candidates", required_output_format["risk_flags"])
        self.assertIn("insufficient_customer_info", required_output_format["risk_flags"])

    def test_rendered_prompt_keeps_chinese_readable_and_requires_json(self) -> None:
        payload = build_model_input_payload(
            record=self._record(),
            candidates=[self._candidate()],
            applicable_memories=[],
        )

        prompt = render_model_prompt(payload)

        self.assertIn("必须只返回 JSON", prompt)
        self.assertIn("海天金标生抽", prompt)
        self.assertIn('"record_id": "C000001"', prompt)
        self.assertIn('"candidate_products"', prompt)
        self.assertIn("brand_conflict", prompt)
        self.assertIn("insufficient_customer_info", prompt)

    def test_parse_valid_model_json_response(self) -> None:
        response_text = """
        {
          "customer_semantic_summary": "海天金标生抽，500ml瓶装。",
          "key_identity_signals": ["海天", "金标", "生抽", "500ml", "瓶"],
          "strong_constraints": ["海天", "生抽", "500ml", "瓶"],
          "weak_constraints": ["金标"],
          "ignored_or_noise_signals": [],
          "missing_or_uncertain_signals": [],
          "candidate_assessments": [
            {
              "candidate_id": "K000001",
              "same_business_identity": true,
              "matched_evidence": ["品牌、品名、规格、单位一致"],
              "conflicts": [],
              "missing_evidence": [],
              "risk_flags": [],
              "summary": "候选完整覆盖客户关键身份信号。"
            }
          ],
          "selected_candidate_id": "K000001",
          "result_status": "strong_auto_code",
          "risk_flags": [],
          "evidence_summary": "品牌、品名、规格、单位一致。",
          "manual_review_reason": "",
          "can_auto_code": true
        }
        """

        decision = parse_model_decision_response(response_text)

        self.assertEqual(decision.result_status.value, "strong_auto_code")
        self.assertTrue(decision.can_auto_code)

    def test_parse_model_json_response_normalizes_common_risk_flag_aliases(self) -> None:
        response_text = """
        {
          "customer_semantic_summary": "客户信息不足。",
          "key_identity_signals": ["信息不足"],
          "strong_constraints": [],
          "weak_constraints": [],
          "ignored_or_noise_signals": [],
          "missing_or_uncertain_signals": ["品牌", "规格"],
          "candidate_assessments": [
            {
              "candidate_id": "K000001",
              "same_business_identity": false,
              "matched_evidence": [],
              "conflicts": [],
              "missing_evidence": [],
              "risk_flags": ["brand_mismatch", "品牌冲突", "multiple_candidates"],
              "summary": "候选存在品牌冲突。"
            }
          ],
          "selected_candidate_id": null,
          "result_status": "manual_review",
          "risk_flags": ["package_mismatch", "unit_mismatch", "包装冲突", "单位冲突", "insufficient_info"],
          "evidence_summary": "需要人工确认。",
          "manual_review_reason": "信息不足。",
          "can_auto_code": false
        }
        """

        decision = parse_model_decision_response(response_text)

        self.assertEqual(
            [flag.value for flag in decision.risk_flags],
            [
                "package_conflict",
                "unit_conflict",
                "package_conflict",
                "unit_conflict",
                "insufficient_customer_info",
            ],
        )
        self.assertEqual(
            [flag.value for flag in decision.candidate_assessments[0].risk_flags],
            ["brand_conflict", "brand_conflict", "multiple_valid_candidates"],
        )

    def test_parse_invalid_json_as_model_error_without_auto_code(self) -> None:
        decision = parse_model_decision_response("不是 JSON")

        self.assertEqual(decision.result_status.value, "model_error")
        self.assertFalse(decision.can_auto_code)
        self.assertIn("无法解析", decision.manual_review_reason)

    def test_parse_schema_violation_as_model_error_without_auto_code(self) -> None:
        response_text = """
        {
          "customer_semantic_summary": "客户信息不足。",
          "result_status": "manual_review",
          "can_auto_code": true
        }
        """

        decision = parse_model_decision_response(response_text)

        self.assertEqual(decision.result_status.value, "model_error")
        self.assertFalse(decision.can_auto_code)
        self.assertIn("格式或规则校验失败", decision.manual_review_reason)


if __name__ == "__main__":
    unittest.main()
