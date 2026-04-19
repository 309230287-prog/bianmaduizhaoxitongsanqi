# Phase 2 Trial Diagnostics

- Source: `samples\phase2\model_trial_results_deepseek_v0.3.xlsx`
- Total rows: 10

## Category Counts
- `invalid_json`: 0
- `schema_validation_error`: 1
- `business_rule_validation_error`: 0
- `model_call_error`: 1
- `empty_output`: 0
- `schema_valid_after_normalization`: 8
- `unknown`: 0

## Acceptance Summary
- `status_match_count`: 6
- `selected_code_match_count`: 2
- `selected_code_mismatch_count`: 6
- `auto_code_count`: 3
- `unsafe_auto_code_count`: 1

## Current Parser Summary
- `current_parser_valid_count`: 8
- `current_status_match_count`: 6
- `current_selected_code_match_count`: 2
- `current_selected_code_mismatch_count`: 5
- `current_unsafe_auto_code_count`: 1

## Representative Samples
### invalid_json
- None

### schema_validation_error
- `GS0026` (manual_or_unmatched): 字段校验失败：risk_flags.0 / enum

### business_rule_validation_error
- None

### model_call_error
- `GS0021` (hidden_info): 模型调用失败: HTTP 307: <html> <head><title>307 Temporary Redirect</title></head> <body> <center><h1>307 Temporary Redirect</…

### empty_output
- None

### schema_valid_after_normalization
- `GS0001` (strong_auto): 历史结果表标记失败，但原始输出经当前风险标记规范化后已通过模型校验
- `GS0002` (strong_auto): 历史结果表标记失败，但原始输出经当前风险标记规范化后已通过模型校验
- `GS0006` (equivalence): 历史结果表标记失败，但原始输出经当前风险标记规范化后已通过模型校验

### unknown
- None
