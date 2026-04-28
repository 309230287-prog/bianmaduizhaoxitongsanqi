"""Prompt templates for round planning and candidate comparison.

Follows the 003 plan: model commands the system; the system executes, records, and brakes.
"""

from product_code_mapper.domain.models import Candidate, CompanyProduct, CustomerItem
from product_code_mapper.planning.round_command import ALLOWED_ENTRY_DIMENSIONS

ROUND_PLAN_SYSTEM = """你是商品编码对照系统的发令模型。你的职责是分析大自然池中未完成的客户商品，选择一批有共同特征的商品入圈处理。

## 规则

1. 从剩余商品中找出共同特征（品名、品牌、规格范围等），决定本轮入圈维度和入圈词。
2. 入圈维度必须从允许列表中选择。
3. 每一轮必须同时给出入圈词和排除词。只有入圈没有排除是不允许的。
4. 排除词用于防止不同商品身份的商品误入本圈（如"生抽"圈排除"老抽"、"番茄"圈排除"番茄酱"）。
5. 输出必须是合法 JSON，包含所有必填字段。
6. auto_code_policy 必须为 "system_gate_required"。
7. candidate_limit 建议 20，export_candidate_limit 建议 5。

## 允许的入圈维度

{allowed_dimensions}

## 输出 JSON 格式

{output_schema}
"""

ROUND_PLAN_OUTPUT_SCHEMA = """{
  "round_id": "round_001",
  "round_name": "核心品名_生抽",
  "round_goal": "优先处理疑似生抽商品",
  "entry_dimension": "core_product_name",
  "entry_terms": ["生抽"],
  "entry_alias_terms": [],
  "exclude_terms": ["老抽", "蒸鱼豉油", "蚝油"],
  "weak_related_terms": [],
  "must_check_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
  "hard_conflict_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
  "search_strategy": {
    "company_catalog_scope": "global",
    "candidate_limit": 20,
    "export_candidate_limit": 5
  },
  "model_compare_policy": "compare_only_after_candidates",
  "auto_code_policy": "system_gate_required"
}"""

COMPARE_SYSTEM = """你是商品编码对照系统的比较模型。你的职责是比较客户商品记录和我司候选商品，判断它们是否表达同一个业务商品身份。

## 判断原则

1. 核心品名一致是最重要的信号。同义词（番茄=西红柿）视为品名一致。
2. 品牌如果双方都有且不一致，是硬冲突。
3. 规格如果不一致且不能等价换算，是硬冲突。
4. 单位不一致可能影响结算，需要谨慎。
5. 不能脑补客户没写的信息。客户没写品牌，不能擅自推断。
6. 备注可能改变商品身份（如"切丝"vs"切块"）。
7. 如果证据不足以确认，应如实输出"必须人工审核"。
8. 如果有多个候选都合理，不能强行选一个。

## 输出格式

必须是合法 JSON：
{candidate_schema}

## 五档结果状态

- 自动落码：证据完整，核心身份明确，无冲突
- 自动落码但有表达差异：身份一致，但存在文字表达差异
- 建议落码待确认：倾向明显但有小范围不确定
- 必须人工审核：存在硬冲突、信息不足或候选难以区分
- 未找到可靠匹配：候选均不可靠

## 当前判断准绳摘要

- 正确 = 业务商品身份一致，不是名称一样
- 偏差 = 把客户意思理解歪了
- 遗漏 = 客户写了关键信息但系统没纳入
- 自动落码必须有证据，不能靠模型自信
- 品牌冲突、规格冲突、包装冲突一律禁止自动落码
"""

CANDIDATE_OUTPUT_SCHEMA = """{
  "selected_candidate_index": 0,
  "status": "自动落码",
  "reason_summary": "品牌海天一致，品名金标生抽一致，规格500ml一致，单位瓶一致",
  "evidence_summary": "品牌: 一致(海天); 品名: 一致(金标生抽); 规格: 一致(500ml); 单位: 一致(瓶)",
  "risk_summary": "无硬冲突",
  "matched_signals": ["品牌", "品名", "规格", "单位"],
  "unmatched_signals": [],
  "conflict_signals": [],
  "need_manual_review": false
}"""


def build_round_plan_prompt(
    remaining_count: int,
    sample_items: list[CustomerItem],
    completed_dimensions: list[str],
    round_no: int,
) -> str:
    """Build a prompt asking the model to plan the next processing round."""
    allowed_dim_list = "\n".join(f"- `{dim}`" for dim in sorted(ALLOWED_ENTRY_DIMENSIONS))
    system = ROUND_PLAN_SYSTEM.format(
        allowed_dimensions=allowed_dim_list,
        output_schema=ROUND_PLAN_OUTPUT_SCHEMA,
    )

    sample_lines = []
    for item in sample_items[:15]:
        sample_lines.append(f"  - [{item.row_id}] {item.display_text}")
    sample_text = "\n".join(sample_lines) if sample_lines else "（无剩余商品）"

    dim_text = "、".join(completed_dimensions) if completed_dimensions else "（无）"

    user = (
        f"当前是第 {round_no} 轮。大自然池剩余 {remaining_count} 条商品。\n\n"
        f"已使用过的入圈维度：{dim_text}\n\n"
        f"剩余商品样例（最多 15 条）：\n{sample_text}\n\n"
        f"请分析剩余商品，输出下一轮的结构化发令 JSON。只输出 JSON，不要输出其他内容。"
    )
    return f"{system}\n\n{user}"


def build_compare_prompt(
    customer: CustomerItem,
    candidates: list[Candidate],
) -> str:
    """Build a prompt asking the model to compare a customer item with candidates."""
    system = COMPARE_SYSTEM.format(candidate_schema=CANDIDATE_OUTPUT_SCHEMA)

    customer_lines = [f"客户商品 [{customer.row_id}]:"]
    for key, value in customer.fields.items():
        if value:
            customer_lines.append(f"  {key}: {value}")

    candidate_lines = []
    for idx, candidate in enumerate(candidates):
        product = candidate.product
        candidate_lines.append(
            f"候选 {idx}: 编码={product.code}, 名称={product.name}, "
            f"品牌={product.brand or '（无）'}, 规格={product.spec or '（无）'}, "
            f"单位={product.unit or '（无）'}, 包装={product.package or '（无）'}"
        )

    user = (
        "\n".join(customer_lines)
        + "\n\n候选商品：\n"
        + "\n".join(candidate_lines)
        + "\n\n请比较客户商品和各候选，输出结构化比较结果 JSON。只输出 JSON，不要输出其他内容。"
        + "\n如果找不到可靠候选，selected_candidate_index 设为 -1，status 设为 \"未找到可靠匹配\"。"
    )
    return f"{system}\n\n{user}"
