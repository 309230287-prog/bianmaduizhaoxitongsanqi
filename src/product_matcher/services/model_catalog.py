from __future__ import annotations

from dataclasses import dataclass
from typing import Any


BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


@dataclass(frozen=True)
class ModelOption:
    selection_id: str
    provider_name: str
    provider_label: str
    model_name: str
    label: str
    group_label: str
    base_url: str
    api_key_env_name: str
    description: str
    tags: tuple[str, ...] = ()
    recommended: bool = False
    custom: bool = False

    def to_picker_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "provider_name": self.provider_name,
            "provider_label": self.provider_label,
            "model_name": self.model_name,
            "label": self.label,
            "group_label": self.group_label,
            "base_url": self.base_url,
            "api_key_env_name": self.api_key_env_name,
            "description": self.description,
            "tags": list(self.tags),
            "recommended": self.recommended,
            "custom": self.custom,
        }


MODEL_OPTIONS: tuple[ModelOption, ...] = (
    ModelOption(
        selection_id="auto:recommended",
        provider_name="bailian",
        provider_label="阿里云百炼",
        model_name="qwen-plus",
        label="Auto 推荐",
        group_label="Auto 推荐",
        base_url=BAILIAN_BASE_URL,
        api_key_env_name="DASHSCOPE_API_KEY",
        description="让系统使用当前推荐的生产模型。当前映射为 qwen-plus。",
        tags=("推荐", "结构化输出", "语义判断"),
        recommended=True,
    ),
    ModelOption(
        selection_id="bailian:qwen-plus",
        provider_name="bailian",
        provider_label="阿里云百炼",
        model_name="qwen-plus",
        label="qwen-plus",
        group_label="推荐模型",
        base_url=BAILIAN_BASE_URL,
        api_key_env_name="DASHSCOPE_API_KEY",
        description="当前二期语义翻译默认模型，优先用于金样本试跑。",
        tags=("推荐", "结构化输出", "中文语义", "性价比"),
        recommended=True,
    ),
    ModelOption(
        selection_id="bailian:custom",
        provider_name="bailian",
        provider_label="阿里云百炼",
        model_name="",
        label="百炼自定义模型名",
        group_label="阿里云百炼",
        base_url=BAILIAN_BASE_URL,
        api_key_env_name="DASHSCOPE_API_KEY",
        description="使用阿里云百炼兼容接口，但手动填写模型名。",
        tags=("自定义", "OpenAI Compatible"),
        custom=True,
    ),
    ModelOption(
        selection_id="deepseek:deepseek-chat",
        provider_name="deepseek",
        provider_label="DeepSeek",
        model_name="deepseek-chat",
        label="deepseek-chat",
        group_label="DeepSeek",
        base_url=DEEPSEEK_BASE_URL,
        api_key_env_name="DEEPSEEK_API_KEY",
        description="DeepSeek 官方 OpenAI-compatible 聊天模型，适合中文语义判断试跑。",
        tags=("中文语义", "结构化输出", "OpenAI Compatible"),
        recommended=False,
    ),
    ModelOption(
        selection_id="deepseek:deepseek-reasoner",
        provider_name="deepseek",
        provider_label="DeepSeek",
        model_name="deepseek-reasoner",
        label="deepseek-reasoner",
        group_label="DeepSeek",
        base_url=DEEPSEEK_BASE_URL,
        api_key_env_name="DEEPSEEK_API_KEY",
        description="DeepSeek 官方推理模型，适合复杂证据推理；试跑时成本和延迟可能更高。",
        tags=("推理", "中文语义", "OpenAI Compatible"),
        recommended=False,
    ),
    ModelOption(
        selection_id="custom:openai-compatible",
        provider_name="openai_compatible",
        provider_label="OpenAI Compatible",
        model_name="",
        label="自定义兼容模型",
        group_label="OpenAI Compatible",
        base_url="",
        api_key_env_name="OPENAI_API_KEY",
        description="用于第三方或本地 OpenAI-compatible /chat/completions 接口。",
        tags=("自定义", "第三方", "本地模型"),
        custom=True,
    ),
)


GROUP_ORDER = ("Auto 推荐", "推荐模型", "阿里云百炼", "DeepSeek", "OpenAI Compatible", "自定义模型")


def list_model_options() -> list[ModelOption]:
    return list(MODEL_OPTIONS)


def list_model_picker_groups() -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {label: [] for label in GROUP_ORDER}
    for option in MODEL_OPTIONS:
        group_label = option.group_label
        groups.setdefault(group_label, []).append(option.to_picker_dict())

    groups["自定义模型"] = [
        option.to_picker_dict()
        for option in MODEL_OPTIONS
        if option.custom and option.group_label != "自定义模型"
    ]
    return [
        {"label": label, "options": options}
        for label in GROUP_ORDER
        if (options := groups.get(label))
    ]


def find_model_option(selection_id: str) -> ModelOption:
    normalized_selection_id = (selection_id or "auto:recommended").strip()
    for option in MODEL_OPTIONS:
        if option.selection_id == normalized_selection_id:
            return option
    raise ValueError(f"未知模型选择：{selection_id}")


def apply_model_selection(
    settings: dict[str, Any],
    selection_id: str,
    *,
    custom_base_url: str = "",
    custom_model_name: str = "",
) -> dict[str, Any]:
    option = find_model_option(selection_id)
    selected = dict(settings)
    selected["model_selection_id"] = option.selection_id
    selected["provider_name"] = option.provider_name
    if option.custom:
        selected["base_url"] = (custom_base_url or option.base_url or selected.get("base_url", "")).strip()
        selected["production_model_name"] = (
            custom_model_name or option.model_name or selected.get("production_model_name", "")
        ).strip()
    else:
        selected["base_url"] = (option.base_url or selected.get("base_url", "")).strip()
        selected["production_model_name"] = (option.model_name or selected.get("production_model_name", "")).strip()
    selected["api_key_env_name"] = option.api_key_env_name or selected.get("api_key_env_name", "")
    return selected
