from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from product_matcher.paths import CONFIG_DIR, RUNTIME_DIR
from product_matcher.services.model_catalog import apply_model_selection, list_model_picker_groups


MODEL_SETTINGS_EXAMPLE_FILE = CONFIG_DIR / "model_settings.example.json"
MODEL_SETTINGS_DIR = RUNTIME_DIR / "config"
MODEL_SETTINGS_FILE = MODEL_SETTINGS_DIR / "model_settings.json"

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL_NAME = "qwen-plus"
DEFAULT_API_KEY_ENV_NAME = "DASHSCOPE_API_KEY"
ALLOWED_API_KEY_SOURCES = {"env", "local_config"}


class ModelSettingsError(ValueError):
    """Raised when model settings are invalid or unusable."""


def default_model_settings() -> dict[str, Any]:
    return {
        "version": 1,
        "model_selection_id": "auto:recommended",
        "provider_name": "bailian",
        "base_url": DEFAULT_BASE_URL,
        "production_model_name": DEFAULT_MODEL_NAME,
        "api_key_source": "env",
        "api_key_env_name": DEFAULT_API_KEY_ENV_NAME,
        "api_key_value": "",
        "timeout_seconds": 60,
        "max_retries": 2,
    }


def load_model_settings() -> dict[str, Any]:
    settings = default_model_settings()
    if not MODEL_SETTINGS_FILE.exists():
        return settings

    try:
        payload = json.loads(MODEL_SETTINGS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelSettingsError("模型配置文件不是有效的 JSON。") from exc

    if not isinstance(payload, dict):
        raise ModelSettingsError("模型配置文件格式无效。")

    settings.update(payload)
    return _normalize_settings(settings)


def build_settings_from_form(form, existing_settings: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing_settings or default_model_settings()
    source = str(form.get("api_key_source", existing.get("api_key_source", "env"))).strip() or "env"
    has_explicit_model_selection = "model_selection_id" in form
    model_selection_id = str(form.get("model_selection_id", "")).strip()

    api_key_value = str(form.get("api_key_value", "")).strip()
    if source == "local_config" and not api_key_value:
        api_key_value = str(existing.get("api_key_value", "")).strip()
    if source == "env":
        api_key_value = ""

    settings = {
        "version": existing.get("version", 1),
        "model_selection_id": model_selection_id or _infer_legacy_model_selection_id(
            provider_name=str(form.get("provider_name", existing.get("provider_name", "bailian"))).strip(),
            base_url=str(form.get("base_url", existing.get("base_url", DEFAULT_BASE_URL))).strip(),
            model_name=str(
                form.get("production_model_name", existing.get("production_model_name", DEFAULT_MODEL_NAME))
            ).strip(),
        ),
        "provider_name": str(form.get("provider_name", existing.get("provider_name", "bailian"))).strip(),
        "base_url": str(form.get("base_url", existing.get("base_url", DEFAULT_BASE_URL))).strip(),
        "production_model_name": str(
            form.get("production_model_name", existing.get("production_model_name", DEFAULT_MODEL_NAME))
        ).strip(),
        "api_key_source": source,
        "api_key_env_name": str(
            form.get("api_key_env_name", existing.get("api_key_env_name", DEFAULT_API_KEY_ENV_NAME))
        ).strip(),
        "api_key_value": api_key_value,
        "timeout_seconds": form.get("timeout_seconds", existing.get("timeout_seconds", 60)),
        "max_retries": form.get("max_retries", existing.get("max_retries", 2)),
    }
    if has_explicit_model_selection:
        settings = apply_model_selection(
            settings,
            settings["model_selection_id"],
            custom_base_url=settings["base_url"],
            custom_model_name=settings["production_model_name"],
        )
    return _normalize_settings(settings)


def save_model_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_settings(settings)
    MODEL_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_SETTINGS_FILE.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def resolve_runtime_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_settings(settings)
    api_key = ""
    if normalized["api_key_source"] == "env":
        env_name = normalized["api_key_env_name"]
        api_key = os.environ.get(env_name, "").strip()
        if not api_key:
            raise ModelSettingsError("未读取到环境变量 API Key。")
    else:
        api_key = normalized["api_key_value"].strip()
        if not api_key:
            raise ModelSettingsError("未保存本地 API Key。")

    return {
        "provider_name": normalized["provider_name"],
        "base_url": normalized["base_url"],
        "production_model_name": normalized["production_model_name"],
        "api_key": api_key,
        "timeout_seconds": normalized["timeout_seconds"],
        "max_retries": normalized["max_retries"],
    }


def test_model_connection(settings: dict[str, Any]) -> dict[str, str]:
    runtime = resolve_runtime_settings(settings)
    url = runtime["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": runtime["production_model_name"],
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0,
        "max_tokens": 1,
    }
    request_body = json.dumps(payload).encode("utf-8")
    request = urllib_request.Request(
        url,
        data=request_body,
        headers={
            "Authorization": f"Bearer {runtime['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=runtime["timeout_seconds"]) as response:
            response_body = response.read().decode("utf-8")
            status_code = getattr(response, "status", 200)
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        detail = detail[:160].strip() if detail else ""
        raise ModelSettingsError(f"模型连接测试失败：HTTP {exc.code} {detail}".strip()) from exc
    except urllib_error.URLError as exc:
        raise ModelSettingsError(f"模型连接测试失败：{exc.reason}") from exc

    if status_code < 200 or status_code >= 300:
        raise ModelSettingsError(f"模型连接测试失败：HTTP {status_code}")

    try:
        payload = json.loads(response_body) if response_body else {}
    except json.JSONDecodeError as exc:
        raise ModelSettingsError("模型连接测试失败：返回结果不是有效 JSON。") from exc

    if isinstance(payload, dict) and payload.get("error"):
        error_payload = payload["error"]
        if isinstance(error_payload, dict):
            message = str(error_payload.get("message", "未知错误")).strip()
        else:
            message = str(error_payload).strip()
        raise ModelSettingsError(f"模型连接测试失败：{message}")

    return {
        "provider_name": runtime["provider_name"],
        "production_model_name": runtime["production_model_name"],
        "message": "模型连接测试通过。",
    }


def describe_model_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_settings(settings)
    local_key_saved = bool(normalized["api_key_value"].strip())
    if normalized["api_key_source"] == "env":
        api_key_display = f"环境变量：{normalized['api_key_env_name']}"
    elif local_key_saved:
        api_key_display = "本地保存：已保存"
    else:
        api_key_display = "本地保存：未保存"

    return {
        "provider_name": normalized["provider_name"],
        "provider_label": _provider_label(normalized["provider_name"]),
        "model_selection_id": normalized["model_selection_id"],
        "base_url": normalized["base_url"],
        "production_model_name": normalized["production_model_name"],
        "api_key_source": normalized["api_key_source"],
        "api_key_env_name": normalized["api_key_env_name"],
        "api_key_value": "",
        "api_key_display": api_key_display,
        "local_key_saved": local_key_saved,
        "timeout_seconds": normalized["timeout_seconds"],
        "max_retries": normalized["max_retries"],
        "runtime_file": str(MODEL_SETTINGS_FILE),
        "example_file": str(MODEL_SETTINGS_EXAMPLE_FILE),
        "model_picker_groups": list_model_picker_groups(),
    }


def recommended_model_settings() -> dict[str, Any]:
    return default_model_settings()


def _normalize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = default_model_settings()
    normalized.update(settings)

    normalized["provider_name"] = str(normalized.get("provider_name", "")).strip() or "bailian"
    normalized["model_selection_id"] = str(normalized.get("model_selection_id", "")).strip() or "custom:openai-compatible"
    normalized["base_url"] = str(normalized.get("base_url", "")).strip().rstrip("/")
    normalized["production_model_name"] = str(normalized.get("production_model_name", "")).strip()
    normalized["api_key_source"] = str(normalized.get("api_key_source", "env")).strip() or "env"
    normalized["api_key_env_name"] = str(normalized.get("api_key_env_name", "")).strip() or DEFAULT_API_KEY_ENV_NAME
    normalized["api_key_value"] = str(normalized.get("api_key_value", "")).strip()
    normalized["version"] = _to_int(normalized.get("version", 1), "配置版本")
    normalized["timeout_seconds"] = _to_int(normalized.get("timeout_seconds", 60), "请求超时")
    normalized["max_retries"] = _to_int(normalized.get("max_retries", 2), "失败重试次数")

    if not normalized["base_url"]:
        raise ModelSettingsError("未配置 Base URL。")
    if not normalized["production_model_name"]:
        raise ModelSettingsError("未配置生产模型名。")
    if normalized["api_key_source"] not in ALLOWED_API_KEY_SOURCES:
        raise ModelSettingsError("API Key 来源无效。")
    if normalized["timeout_seconds"] <= 0:
        raise ModelSettingsError("请求超时必须大于 0。")
    if normalized["max_retries"] < 0:
        raise ModelSettingsError("失败重试次数不能小于 0。")
    if normalized["api_key_source"] == "env" and not normalized["api_key_env_name"]:
        raise ModelSettingsError("未配置环境变量名。")
    if normalized["api_key_source"] == "local_config" and not normalized["api_key_value"]:
        raise ModelSettingsError("未保存本地 API Key。")

    return normalized


def _to_int(value: Any, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ModelSettingsError(f"{label}格式无效。") from exc


def _infer_legacy_model_selection_id(provider_name: str, base_url: str, model_name: str) -> str:
    if provider_name == "bailian":
        if base_url.rstrip("/") == DEFAULT_BASE_URL and model_name == DEFAULT_MODEL_NAME:
            return "auto:recommended"
        return "bailian:custom"
    return "custom:openai-compatible"


def _provider_label(provider_name: str) -> str:
    if provider_name == "bailian":
        return "阿里云百炼"
    if provider_name == "deepseek":
        return "DeepSeek"
    if provider_name == "openai_compatible":
        return "OpenAI Compatible"
    return provider_name
