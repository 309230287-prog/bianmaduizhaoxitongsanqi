"""003 验证样本测试 — 覆盖执行计划要求的所有风险类型。

验证标准（来自 003 方案 §14.3 和需求文档 §20）:
- 自动落码严重错误必须为 0
- 严重错误包括: 核心品名错、品牌冲突、规格包装冲突、系统脑补
- 错圈商品必须能回流
- 弱相关不能自动落码
"""

from product_code_mapper.candidates.executor import CandidateExecutor
from product_code_mapper.domain.models import CompanyProduct, CustomerItem, MatchResult
from product_code_mapper.domain.statuses import MatchStatus
from product_code_mapper.matching.auto_code_gate import AutoCodeGate
from product_code_mapper.model.client import FakeModelClient
from product_code_mapper.planning.round_command import RoundCommand
from product_code_mapper.pool.nature_pool import NaturePool
from product_code_mapper.runs.engine import MatchRunEngine


# ── Test catalog ──

def _test_catalog():
    """模拟我司商品库"""
    return [
        CompanyProduct(code="P001", name="海天金标生抽", brand="海天", spec="500ml", unit="瓶"),
        CompanyProduct(code="P002", name="海天老抽", brand="海天", spec="500ml", unit="瓶"),
        CompanyProduct(code="P003", name="番茄", brand="", spec="散称", unit="斤"),
        CompanyProduct(code="P004", name="西红柿", brand="", spec="散称", unit="斤"),
        CompanyProduct(code="P005", name="番茄酱", brand="亨氏", spec="300g", unit="瓶"),
        CompanyProduct(code="P006", name="海天金标生抽", brand="海天", spec="1.9L", unit="桶"),
        CompanyProduct(code="P007", name="可乐", brand="可口可乐", spec="330ml", unit="罐"),
        CompanyProduct(code="P008", name="瘦肉", brand="", spec="散称", unit="斤"),
        CompanyProduct(code="P009", name="瘦肉片", brand="", spec="散称", unit="斤"),
        CompanyProduct(code="P010", name="瘦肉丝", brand="", spec="散称", unit="斤"),
    ]


# ── 验证 1: 完全同名商品应能自动落码 ──

def test_003_exact_same_product_auto_codes():
    company = _test_catalog()
    items = [
        CustomerItem(row_id="r1", original_row_index=2, fields={
            "商品名称": "海天金标生抽", "品牌": "海天", "规格": "500ml", "单位": "瓶",
        }),
    ]
    result = MatchRunEngine(model_client=FakeModelClient()).run_once(items, company)
    row = result.row_results.get("r1")
    assert row is not None
    assert row.status == MatchStatus.AUTO_CODE
    assert row.selected_candidate.product.code == "P001"


# ── 验证 2: 番茄应该匹配番茄而非番茄酱 ──

def test_003_fanqie_not_matched_to_fanqie_jiang():
    company = _test_catalog()
    items = [
        CustomerItem(row_id="r1", original_row_index=2, fields={
            "商品名称": "番茄", "规格": "散称", "单位": "斤",
        }),
    ]
    # 番茄酱含"番茄"字眼但不应是首选
    executor = CandidateExecutor(company)
    command = RoundCommand.from_payload({
        "round_id": "r001", "round_name": "核心品名_番茄", "round_goal": "处理番茄",
        "entry_dimension": "core_product_name", "entry_terms": ["番茄"],
        "exclude_terms": ["番茄酱", "番茄沙司"],
        "must_check_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
        "hard_conflict_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
        "search_strategy": {"company_catalog_scope": "global", "candidate_limit": 20, "export_candidate_limit": 5},
        "model_compare_policy": "compare_only_after_candidates",
        "auto_code_policy": "system_gate_required",
    })
    candidates = executor.find_candidates(items[0], command)
    # 番茄酱在排除词中，不应出现
    codes = [c.product.code for c in candidates]
    assert "P005" not in codes  # 番茄酱被排除


# ── 验证 3: 规格冲突不能自动落码 ──

def test_003_spec_conflict_blocks_auto_code():
    product_500ml = CompanyProduct(code="P001", name="海天金标生抽", brand="海天", spec="500ml", unit="瓶")
    item = CustomerItem(row_id="r1", original_row_index=2, fields={
        "商品名称": "海天金标生抽", "品牌": "海天", "规格": "500ml", "单位": "瓶",
    })
    candidate_1_9l = CompanyProduct(code="P006", name="海天金标生抽", brand="海天", spec="1.9L", unit="桶")

    # 正确候选应通过
    from product_code_mapper.domain.models import Candidate
    decision_correct = AutoCodeGate().evaluate(
        item,
        Candidate(product=product_500ml, score=100),
        evidence={"reason": "品牌、品名、规格、单位一致", "matched_signals": ["品牌", "品名", "规格", "单位"]},
    )
    assert decision_correct.can_auto_code

    # 规格冲突的候选应被拦截
    decision_conflict = AutoCodeGate().evaluate(
        item,
        Candidate(product=candidate_1_9l, score=95),
        evidence={"reason": "品牌品名一致但规格不同", "matched_signals": ["品牌", "品名"], "conflict_signals": ["规格"]},
    )
    assert not decision_conflict.can_auto_code
    assert "规格" in decision_conflict.block_reasons


# ── 验证 4: 品牌冲突不能自动落码 ──

def test_003_brand_conflict_blocks_auto_code():
    item = CustomerItem(row_id="r1", original_row_index=2, fields={
        "商品名称": "海天金标生抽", "品牌": "海天", "规格": "500ml", "单位": "瓶",
    })
    wrong_brand = CompanyProduct(code="P999", name="海天金标生抽", brand="厨邦", spec="500ml", unit="瓶")

    from product_code_mapper.domain.models import Candidate
    decision = AutoCodeGate().evaluate(
        item,
        Candidate(product=wrong_brand, score=95),
        evidence={"reason": "品名一致", "matched_signals": ["品名"], "conflict_signals": ["品牌"]},
    )
    assert not decision.can_auto_code


# ── 验证 5: 五轮后进入疑难池 ──

def test_003_item_moves_to_hard_case_after_max_rounds():
    item = CustomerItem(row_id="r1", original_row_index=2, fields={"商品名称": "未知商品"})
    pool = NaturePool([item], max_rounds_per_item=5)
    for i in range(5):
        pool.record_return("r1", dimension=f"dim-{i}", reason="证据不足")
    assert "r1" in pool.hard_case_row_ids


# ── 验证 6: 备注可能改变商品身份 ──

def test_003_note_changes_identity_blocks_auto_code():
    item = CustomerItem(row_id="r1", original_row_index=2, fields={
        "商品名称": "瘦肉丝", "单位": "斤", "备注": "切丝",
    })
    product = CompanyProduct(code="P009", name="瘦肉片", brand="", spec="散称", unit="斤")

    from product_code_mapper.domain.models import Candidate
    decision = AutoCodeGate().evaluate(
        item,
        Candidate(product=product, score=90),
        evidence={"reason": "品名相似", "matched_signals": ["品名"]},
    )
    # 备注中有"切丝"，候选是"瘦肉片"，不匹配
    assert not decision.can_auto_code


# ── 验证 7: 排除词生效 ──

def test_003_exclude_terms_block_wrong_items():
    products = [
        CompanyProduct(code="P001", name="海天金标生抽", brand="海天", spec="500ml", unit="瓶"),
        CompanyProduct(code="P002", name="海天老抽", brand="海天", spec="500ml", unit="瓶"),
    ]
    item = CustomerItem(row_id="r1", original_row_index=2, fields={
        "商品名称": "海天金标生抽", "规格": "500ml", "单位": "瓶",
    })
    command = RoundCommand.from_payload({
        "round_id": "r001", "round_name": "核心品名_生抽", "round_goal": "处理生抽",
        "entry_dimension": "core_product_name", "entry_terms": ["生抽"],
        "exclude_terms": ["老抽"],
        "must_check_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
        "hard_conflict_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
        "search_strategy": {"company_catalog_scope": "global", "candidate_limit": 20, "export_candidate_limit": 5},
        "model_compare_policy": "compare_only_after_candidates",
        "auto_code_policy": "system_gate_required",
    })
    executor = CandidateExecutor(products)
    candidates = executor.find_candidates(item, command)
    codes = [c.product.code for c in candidates]
    assert "P002" not in codes  # 老抽被排除


# ── 验证 8: 我司库缺失时不应自动落码 ──

def test_003_no_candidates_returns_no_match():
    products = [CompanyProduct(code="P001", name="可乐", brand="可口可乐", spec="330ml", unit="罐")]
    item = CustomerItem(row_id="r1", original_row_index=2, fields={
        "商品名称": "雪碧", "规格": "500ml", "单位": "瓶",
    })
    result = MatchRunEngine(model_client=FakeModelClient()).run_once([item], products)
    row = result.row_results.get("r1")
    assert row is not None
    assert row.status in (MatchStatus.NO_RELIABLE_MATCH, MatchStatus.SUGGESTED_REVIEW)


# ── 验证 9: 整行记录语义理解（多字段综合判断） ──

def test_003_multi_field_semantic_matching():
    """验证引擎不只靠商品名称，而是综合品牌+规格+单位判断"""
    company = _test_catalog()
    # 只给商品名称，没有品牌规格单位 — 匹配可能性多但需综合判断
    items = [
        CustomerItem(row_id="r1", original_row_index=2, fields={
            "商品名称": "海天金标生抽", "品牌": "海天", "规格": "500ml", "单位": "瓶",
        }),
    ]
    result = MatchRunEngine(model_client=FakeModelClient()).run_once(items, company)
    row = result.row_results.get("r1")
    assert row is not None
    # 应匹配到 500ml 瓶装的而非 1.9L 桶装的
    if row.selected_candidate:
        assert row.selected_candidate.product.spec == "500ml"
        assert row.selected_candidate.product.unit == "瓶"


# ── 验证 10: 引擎返回完整统计 ──

def test_003_engine_returns_full_metrics():
    company = _test_catalog()
    items = [
        CustomerItem(row_id="r1", original_row_index=2, fields={
            "商品名称": "海天金标生抽", "品牌": "海天", "规格": "500ml", "单位": "瓶",
        }),
        CustomerItem(row_id="r2", original_row_index=3, fields={
            "商品名称": "番茄酱", "规格": "300g", "单位": "瓶",
        }),
    ]
    result = MatchRunEngine(model_client=FakeModelClient()).run_once(items, company)
    # 统计字段应齐全
    assert result.metrics.total_count == 2
    assert result.metrics.total_count == (
        result.metrics.auto_code_count
        + result.metrics.auto_code_with_diff_count
        + result.metrics.suggested_review_count
        + result.metrics.manual_review_count
        + result.metrics.no_reliable_match_count
    )
    assert result.audit_entries  # 有审计日志
