# Phase 2 Trial Diagnostics

- Source: `samples\phase2\model_trial_results_deepseek_v0.1.xlsx`
- Total rows: 10

## Category Counts
- `invalid_json`: 0
- `schema_validation_error`: 0
- `business_rule_validation_error`: 0
- `model_call_error`: 1
- `empty_output`: 0
- `schema_valid_after_normalization`: 9
- `unknown`: 0

## Representative Samples
### invalid_json
- None

### schema_validation_error
- None

### business_rule_validation_error
- None

### model_call_error
- `GS0021` (hidden_info): 模型调用失败: 模型返回不是有效 JSON。

### empty_output
- None

### schema_valid_after_normalization
- `GS0001` (strong_auto): 历史结果表标记失败，但原始输出经当前风险标记规范化后已通过模型校验
- `GS0002` (strong_auto): 历史结果表标记失败，但原始输出经当前风险标记规范化后已通过模型校验
- `GS0006` (equivalence): 历史结果表标记失败，但原始输出经当前风险标记规范化后已通过模型校验

### unknown
- None
