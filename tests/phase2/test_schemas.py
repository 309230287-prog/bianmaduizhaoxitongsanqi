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

    def test_model_decision_normalizes_common_risk_flag_aliases(self) -> None:
        decision = ModelDecision(
            customer_semantic_summary="客户表达信息不足，候选存在多个可能。",
            key_identity_signals=["信息不足"],
            strong_constraints=[],
            weak_constraints=[],
            ignored_or_noise_signals=[],
            missing_or_uncertain_signals=["品牌", "规格"],
            candidate_assessments=[
                CandidateAssessment(
                    candidate_id="K001",
                    same_business_identity=False,
                    matched_evidence=[],
                    conflicts=[],
                    missing_evidence=[],
                    risk_flags=["brand_mismatch", "品牌冲突", "spec_mismatch", "多个候选"],
                    summary="候选存在品牌和规格冲突。",
                )
            ],
            selected_candidate_id=None,
            result_status=ResultStatus.MANUAL_REVIEW,
            risk_flags=[
                "package_mismatch",
                "unit_mismatch",
                "multiple_candidates",
                "insufficient_info",
                "包装冲突",
                "单位冲突",
                "多个候选",
                "信息不足",
            ],
            evidence_summary="需要人工确认。",
            manual_review_reason="信息不足。",
            can_auto_code=False,
        )

        self.assertEqual(
            decision.risk_flags,
            [
                RiskFlag.PACKAGE_CONFLICT,
                RiskFlag.UNIT_CONFLICT,
                RiskFlag.MULTIPLE_VALID_CANDIDATES,
                RiskFlag.INSUFFICIENT_CUSTOMER_INFO,
                RiskFlag.PACKAGE_CONFLICT,
                RiskFlag.UNIT_CONFLICT,
                RiskFlag.MULTIPLE_VALID_CANDIDATES,
                RiskFlag.INSUFFICIENT_CUSTOMER_INFO,
            ],
        )
        self.assertEqual(
            decision.candidate_assessments[0].risk_flags,
            [
                RiskFlag.BRAND_CONFLICT,
                RiskFlag.BRAND_CONFLICT,
                RiskFlag.SPEC_CONFLICT,
                RiskFlag.MULTIPLE_VALID_CANDIDATES,
            ],
        )

    def test_model_decision_rejects_unknown_risk_flag_aliases(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="未知风险标记。",
                key_identity_signals=[],
                strong_constraints=[],
                weak_constraints=[],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=[],
                candidate_assessments=[
                    CandidateAssessment(
                        candidate_id="K001",
                        same_business_identity=False,
                        matched_evidence=[],
                        conflicts=[],
                        missing_evidence=[],
                        risk_flags=["not_a_real_flag"],
                        summary="未知风险。",
                    )
                ],
                selected_candidate_id=None,
                result_status=ResultStatus.MANUAL_REVIEW,
                risk_flags=[],
                evidence_summary="。",
                manual_review_reason="未知。",
                can_auto_code=False,
            )

    def test_model_decision_infers_risk_flags_from_common_model_phrases(self) -> None:
        decision = ModelDecision(
            customer_semantic_summary="候选存在复杂冲突。",
            candidate_assessments=[
                CandidateAssessment(
                    candidate_id="K001",
                    same_business_identity=False,
                    risk_flags=[
                        "单位和规格冲突可能表示不同包装层级或产品",
                        "客户未表达无糖系列，不能脑补",
                        "候选商品列表为空，无法进行语义匹配。",
                        "无候选商品，无法评估风险。",
                        "名称冲突",
                        "分类冲突",
                        "name_partial_match",
                    ],
                    summary="需要人工审核。",
                )
            ],
            selected_candidate_id=None,
            result_status=ResultStatus.MANUAL_REVIEW,
            risk_flags=[
                "存在其他候选商品在品牌、品名和单位上匹配但规格不同，可能引起混淆",
                "规格信息不完整",
                "单位不一致",
                "multiple candidates with identical matches may indicate duplicates or similar products",
                "规格描述不直接匹配",
                "多个候选匹配",
            ],
            evidence_summary="需要人工确认。",
            manual_review_reason="证据不足。",
            can_auto_code=False,
        )

        self.assertEqual(
            decision.candidate_assessments[0].risk_flags,
            [
                RiskFlag.PACKAGE_CONFLICT,
                RiskFlag.NEEDS_UNSTATED_ASSUMPTION,
                RiskFlag.CANDIDATE_POOL_MISSING_EVIDENCE,
                RiskFlag.CANDIDATE_POOL_MISSING_EVIDENCE,
                RiskFlag.CORE_NAME_UNCERTAIN,
                RiskFlag.CORE_NAME_UNCERTAIN,
                RiskFlag.CORE_NAME_UNCERTAIN,
            ],
        )
        self.assertEqual(
            decision.risk_flags,
            [
                RiskFlag.MULTIPLE_VALID_CANDIDATES,
                RiskFlag.INSUFFICIENT_CUSTOMER_INFO,
                RiskFlag.UNIT_CONFLICT,
                RiskFlag.MULTIPLE_VALID_CANDIDATES,
                RiskFlag.SPEC_CONFLICT,
                RiskFlag.MULTIPLE_VALID_CANDIDATES,
            ],
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

    def test_model_decision_rejects_strong_auto_without_auto_code_flag(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="海天金标生抽，500ml瓶装。",
                key_identity_signals=["海天", "金标", "生抽", "500ml", "瓶"],
                strong_constraints=["海天", "生抽", "500ml", "瓶"],
                weak_constraints=[],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=[],
                candidate_assessments=[
                    CandidateAssessment(
                        candidate_id="K001",
                        same_business_identity=True,
                        matched_evidence=["品牌、品名、规格、单位一致"],
                        conflicts=[],
                        missing_evidence=[],
                        risk_flags=[],
                        summary="完全匹配。",
                    )
                ],
                selected_candidate_id="K001",
                result_status=ResultStatus.STRONG_AUTO_CODE,
                risk_flags=[],
                evidence_summary="证据完整。",
                manual_review_reason="",
                can_auto_code=False,
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

    def test_model_decision_rejects_suggested_code_marked_auto_code(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="可给建议但不能自动落码。",
                key_identity_signals=["白辣椒"],
                strong_constraints=["白辣椒"],
                weak_constraints=[],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=["规格"],
                candidate_assessments=[
                    CandidateAssessment(
                        candidate_id="K001",
                        same_business_identity=False,
                        matched_evidence=["名称匹配"],
                        conflicts=[],
                        missing_evidence=["规格缺失"],
                        risk_flags=[RiskFlag.INSUFFICIENT_CUSTOMER_INFO],
                        summary="只能建议。",
                    )
                ],
                selected_candidate_id="K001",
                result_status=ResultStatus.SUGGESTED_CODE,
                risk_flags=[RiskFlag.INSUFFICIENT_CUSTOMER_INFO],
                evidence_summary="证据不足。",
                manual_review_reason="只能给建议，不能自动。",
                can_auto_code=True,
            )

    def test_model_decision_rejects_unmatched_with_selected_candidate(self) -> None:
        with self.assertRaises(ValidationError):
            ModelDecision(
                customer_semantic_summary="候选池为空或无法解释客户商品。",
                key_identity_signals=["熟咸蛋"],
                strong_constraints=["熟咸蛋"],
                weak_constraints=[],
                ignored_or_noise_signals=[],
                missing_or_uncertain_signals=[],
                candidate_assessments=[],
                selected_candidate_id="K001",
                result_status=ResultStatus.UNMATCHED,
                risk_flags=[RiskFlag.CANDIDATE_POOL_MISSING_EVIDENCE],
                evidence_summary="无可用候选。",
                manual_review_reason="",
                can_auto_code=False,
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
