# 二期黄金样本表结构

## 用途

这张表是二期大模型语义翻译的第一份考试卷。

它不是普通数据清洗表，也不是最终结果表。

每一行都应该有人工确认的标准答案，用来验证：

- 大模型是否理解客户商品记录
- 大模型是否能对齐我司商品
- 大模型是否会脑补
- 大模型是否会遗漏规格、包装、单位、备注等关键信息
- 大模型是否能正确区分自动落码和人工审核

## 样本数量

第一版先做 30 条黄金样本。

建议覆盖：

- 5 条明显可强自动落码样本
- 5 条表达差异但业务等价样本
- 5 条规格或包装风险样本
- 5 条品牌、系列或等级风险样本
- 5 条备注或名称隐藏信息样本
- 5 条必须人工或无法匹配样本

## 字段说明

| 字段名 | 必填 | 说明 |
| --- | --- | --- |
| sample_id | 是 | 样本编号，例如 GS0001 |
| sample_group | 是 | 样本类型，例如 strong_auto、equivalence、package_risk、brand_series_risk、hidden_info、manual_or_unmatched |
| customer_row_number | 否 | 客户库原始行号 |
| customer_name | 是 | 客户原始商品名称 |
| customer_spec | 否 | 客户规格 |
| customer_unit | 否 | 客户单位 |
| customer_category | 否 | 客户类别 |
| customer_brand | 否 | 客户品牌，如原表无品牌列可为空 |
| customer_remark | 否 | 客户备注或补充信息 |
| customer_other_fields | 否 | 其他有价值字段，建议用 JSON 或简短文本 |
| expected_company_code | 否 | 人工确认的我司商品编码；无匹配时为空 |
| expected_company_name | 否 | 人工确认的我司商品名称；无匹配时为空 |
| expected_company_spec | 否 | 我司规格或描述中的关键规格 |
| expected_company_unit | 否 | 我司单位 |
| expected_result_status | 是 | strong_auto_code、weak_auto_code、suggested_code、manual_review、unmatched |
| human_reason | 是 | 人工为什么这样判断 |
| key_identity_signals | 是 | 核心身份信号，例如 生抽 |
| strong_constraints | 否 | 强约束，例如 海天、金标、500ml、瓶 |
| weak_constraints | 否 | 弱约束，例如 调味品 |
| noise_or_display_terms | 否 | 噪声或展示词 |
| bias_risk | 否 | 可能的偏差风险 |
| omission_risk | 否 | 可能的遗漏风险 |
| allow_auto_code | 是 | yes 或 no |
| manual_review_reason | 否 | 不能自动落码时的原因 |

## 状态说明

`strong_auto_code`：

证据完整，核心身份和强约束无冲突，可以强自动落码。

`weak_auto_code`：

存在表达差异，但业务上已有稳定等价关系，可以弱自动落码并留痕。

`suggested_code`：

第一候选明显更强，但还需要人工快速确认或抽查。

`manual_review`：

存在可能影响商品身份、价格、单位、包装或结算的风险，必须人工审核。

`unmatched`：

没有可靠我司候选，或客户信息不足无法判断。

## 填写原则

- 不确定时不要写自动落码。
- 客户原文没有表达的信息，不要人工脑补成事实。
- 规格、单位、包装、品牌、备注中会改变商品身份的信息必须写进强约束或风险字段。
- 无匹配样本也要保留，它们对验证模型是否乱猜很重要。

