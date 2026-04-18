from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from product_matcher.services.ai_client import chat_json
from product_matcher_phase2.model_trial import (
    ModelCaller,
    load_trial_cases_jsonl,
    run_trial_cases,
    summarize_trial_results,
    write_trial_results_xlsx,
)


PHASE2_SYSTEM_PROMPT = (
    "你是商品编码对照系统二期的语义判断模型。"
    "你的任务是判断客户商品与候选我司商品是否为同一业务商品身份。"
    "必须只输出 JSON 对象，不要输出 Markdown。"
    "不能脑补客户没有表达的品牌、规格、单位、包装层级、系列或等级。"
    "证据不够唯一时，必须输出 manual_review，不能自动落码。"
)


ChatJsonFunc = Callable[..., dict[str, Any]]


def build_chat_json_model_caller(
    runtime_settings: dict[str, Any],
    chat_json_func: ChatJsonFunc = chat_json,
) -> ModelCaller:
    def call_model(payload: dict[str, Any]) -> dict[str, Any]:
        return chat_json_func(
            runtime_settings,
            PHASE2_SYSTEM_PROMPT,
            payload,
            temperature=0.0,
            max_tokens=2400,
        )

    return call_model


def run_trial_from_files(
    input_path: str | Path,
    output_path: str | Path,
    model_caller: ModelCaller,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    cases = load_trial_cases_jsonl(input_path)
    if limit is not None:
        cases = cases[:limit]
    results = run_trial_cases(cases, model_caller)
    write_trial_results_xlsx(results, output_path)
    return summarize_trial_results(results)
