import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.schemas import (
    CandidateAssessment,
    CandidateItem,
    CompanyProduct,
    CustomerRecord,
    ModelDecision,
    ResultStatus,
    RiskFlag,
)


class Phase2SchemaTests(unittest.TestCase):
    def test_customer_record_preserves_raw_and_mapped_fields(self) -> None:
        record = CustomerRecord(
            record_id="C000001",
            source_row_number=2,
            raw_fields={"商品名称": "海天金标生抽", "规格": "500ml", "单位": "瓶"},
            mapped_fields={"name": "海天金标生抽", "spec": "500ml", "unit": "瓶"},
        )

        self.assertEqual(record.raw_fields["商品名称"], "海天金标生抽")
        self.assertEqual(record.mapped_fields["spec"], "500ml")

    def test_model_decision_accepts_strong_auto_without_risks(self) -> None:
        decision = ModelDecision(
            customer_semantic_summary="海天品牌金标系列生抽，500ml瓶装。",
            key_identity_signals=["生抽"],
            strong_constraints=["海天", "金标", "500ml", "瓶"],
            weak_constraints=["调味品"],
            ignored_or_noise_signals=[],
            missing_or_uncertain_signals=[],
            candidate_assessments=[
                CandidateAssessment(
                    candidate_id="K001",
                    same_business_identity=True,
                    matched_evidence=["品牌一致", "品名一致", "规格一致", "单位一致"],
                    conflicts=[],
                    missing_evidence=[],
                    risk_flags=[],
                    summary="候选完整覆盖客户关键身份信号。",
                )
            ],
            selected_candidate_id="K001",
            result_status=ResultStatus.STRONG_AUTO_CODE,
            risk_flags=[],
            evidence_summary="品牌、品名、规格和单位均一致。",
            manual_review_reason="",
            can_auto_code=True,
        )

        self.assertTrue(decision.can_auto_code)
        self.assertEqual(decision.result_status, ResultStatus.STRONG_AUTO_CODE)

    def test_model_decision_rejects_auto_code_with_hard_conflict(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="可口可乐整件商品。",
                key_identity_signals=["可口可乐"],
                strong_constraints=["1*24*330ml", "件"],
                weak_constraints=[],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=[],
                candidate_assessments=[],
                selected_candidate_id="K001",
                result_status=ResultStatus.STRONG_AUTO_CODE,
                risk_flags=[RiskFlag.PACKAGE_CONFLICT],
                evidence_summary="模型错误地忽略了包装层级冲突。",
                manual_review_reason="",
                can_auto_code=True,
            )

    def test_model_decision_rejects_strong_auto_when_selected_assessment_has_hard_conflict(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="客户是整件商品。",
                key_identity_signals=["可口可乐"],
                strong_constraints=["1*24*330ml", "件"],
                weak_constraints=[],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=[],
                candidate_assessments=[
                    CandidateAssessment(
                        candidate_id="K001",
                        same_business_identity=False,
                        matched_evidence=["名称相似"],
                        conflicts=["包装层级冲突"],
                        missing_evidence=[],
                        risk_flags=[RiskFlag.PACKAGE_CONFLICT],
                        summary="候选存在包装层级冲突。",
                    )
                ],
                selected_candidate_id="K001",
                result_status=ResultStatus.STRONG_AUTO_CODE,
                risk_flags=[],
                evidence_summary="模型错误地只在候选评估里记录冲突。",
                manual_review_reason="",
                can_auto_code=True,
            )

    def test_model_decision_rejects_strong_auto_without_selected_candidate_assessment(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="海天金标生抽，500ml瓶装。",
                key_identity_signals=["海天", "金标", "生抽", "500ml", "瓶"],
                strong_constraints=["海天", "生抽", "500ml", "瓶"],
                weak_constraints=["金标"],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=[],
                candidate_assessments=[],
                selected_candidate_id="K001",
                result_status=ResultStatus.STRONG_AUTO_CODE,
                risk_flags=[],
                evidence_summary="缺少被选候选的评估证据。",
                manual_review_reason="",
                can_auto_code=True,
            )

    def test_model_decision_rejects_manual_review_marked_auto_code(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="客户信息不足。",
                key_identity_signals=[],
                strong_constraints=[],
                weak_constraints=[],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=["品牌", "规格"],
                candidate_assessments=[],
                selected_candidate_id=None,
                result_status=ResultStatus.MANUAL_REVIEW,
                risk_flags=[RiskFlag.INSUFFICIENT_CUSTOMER_INFO],
                evidence_summary="缺少关键约束。",
                manual_review_reason="信息不足，需要人工确认。",
                can_auto_code=True,
            )

    def test_model_decision_rejects_weak_auto_without_selected_candidate(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="客户表达与我司表达存在等价关系。",
                key_identity_signals=["番茄", "西红柿"],
                strong_constraints=["斤"],
                weak_constraints=["番茄与西红柿等价"],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=[],
                candidate_assessments=[],
                selected_candidate_id=None,
                result_status=ResultStatus.WEAK_AUTO_CODE,
                risk_flags=[],
                evidence_summary="缺少被选候选。",
                manual_review_reason="",
                can_auto_code=True,
            )

    def test_model_decision_rejects_weak_auto_when_selected_assessment_has_hard_conflict(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="客户是整件商品。",
                key_identity_signals=["可口可乐"],
                strong_constraints=["1*24*330ml", "件"],
                weak_constraints=[],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=[],
                candidate_assessments=[
                    CandidateAssessment(
                        candidate_id="K001",
                        same_business_identity=True,
                        matched_evidence=["名称相似"],
                        conflicts=["包装层级冲突"],
                        missing_evidence=[],
                        risk_flags=[RiskFlag.PACKAGE_CONFLICT],
                        summary="候选存在包装层级冲突。",
                    )
                ],
                selected_candidate_id="K001",
                result_status=ResultStatus.WEAK_AUTO_CODE,
                risk_flags=[],
                evidence_summary="硬冲突不能弱自动落码。",
                manual_review_reason="",
                can_auto_code=True,
            )

    def test_candidate_item_keeps_candidate_source_reasons(self) -> None:
        company_product = CompanyProduct(
            product_id="SPU123",
            code="SPU123",
            name="海天金标生抽500ml",
            unit="瓶",
            alias="",
            description="500ml",
            category_path=["干调类", "调味品", "调味品"],
            raw_fields={},
        )
        candidate = CandidateItem(
            candidate_id="K001",
            product=company_product,
            candidate_sources=["brand_match", "name_contains", "spec_match"],
            candidate_notes="品牌、品名、规格均有明显对应。",
        )

        self.assertIn("spec_match", candidate.candidate_sources)
        self.assertEqual(candidate.product.name, "海天金标生抽500ml")


if __name__ == "__main__":
    unittest.main()
