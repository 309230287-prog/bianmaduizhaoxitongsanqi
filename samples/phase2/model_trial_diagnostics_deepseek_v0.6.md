# Phase 2 Trial Diagnostics

- Source: `samples\phase2\model_trial_results_deepseek_v0.6.xlsx`
- Total rows: 10

## Category Counts
- `invalid_json`: 0
- `schema_validation_error`: 0
- `business_rule_validation_error`: 0
- `model_call_error`: 0
- `empty_output`: 0
- `schema_valid_after_normalization`: 10
- `unknown`: 0

## Acceptance Summary
- `status_match_count`: 8
- `selected_code_match_count`: 4
- `selected_code_mismatch_count`: 4
- `auto_code_count`: 4
- `unsafe_auto_code_count`: 2

## Current Parser Summary
- `current_parser_valid_count`: 10
- `current_status_match_count`: 8
- `current_selected_code_match_count`: 4
- `current_selected_code_mismatch_count`: 4
- `current_unsafe_auto_code_count`: 0

## Representative Samples
### invalid_json
- None

### schema_validation_error
- None

### business_rule_validation_error
- None

### model_call_error
- None

### empty_output
- None

### schema_valid_after_normalization
- `GS0001` (strong_auto): 历史结果表标记失败，但原始输出经当前风险标记规范化后已通过模型校验
- `GS0002` (strong_auto): 历史结果表标记失败，但原始输出经当前风险标记规范化后已通过模型校验
- `GS0006` (equivalence): 历史结果表标记失败，但原始输出经当前风险标记规范化后已通过模型校验

### unknown
- None
