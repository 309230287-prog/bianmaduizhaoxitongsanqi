from __future__ import annotations

import json
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


class AIClientError(RuntimeError):
    """Raised when the upstream model call fails."""


def chat_json(
    runtime_settings: dict[str, Any],
    system_prompt: str,
    user_payload: dict[str, Any],
    *,
    temperature: float = 0.0,
    max_tokens: int = 1200,
) -> dict[str, Any]:
    payload = {
        "model": runtime_settings["production_model_name"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib_request.Request(
        runtime_settings["base_url"].rstrip("/") + "/chat/completions",
        data=request_body,
        headers={
            "Authorization": f"Bearer {runtime_settings['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    last_error: Exception | None = None
    attempts = max(int(runtime_settings.get("max_retries", 0)) + 1, 1)
    for _ in range(attempts):
        try:
            with urllib_request.urlopen(request, timeout=runtime_settings["timeout_seconds"]) as response:
                response_body = response.read().decode("utf-8")
            data = json.loads(response_body)
            content = _extract_message_content(data)
            return _parse_json_object(content)
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            message = detail[:240].strip() if detail else str(exc)
            last_error = AIClientError(f"HTTP {exc.code}: {message}")
        except urllib_error.URLError as exc:
            last_error = AIClientError(f"网络请求失败: {exc.reason}")
        except (json.JSONDecodeError, AIClientError) as exc:
            last_error = exc

    raise AIClientError(f"模型调用失败: {last_error}") from last_error


def _extract_message_content(response_payload: dict[str, Any]) -> str:
    if response_payload.get("error"):
        error_payload = response_payload["error"]
        if isinstance(error_payload, dict):
            message = str(error_payload.get("message", "未知错误")).strip()
        else:
            message = str(error_payload).strip()
        raise AIClientError(message or "未知错误")

    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIClientError("模型返回缺少 choices。")

    message = choices[0].get("message", {})
    if not isinstance(message, dict):
        raise AIClientError("模型返回缺少 message。")

    content = message.get("content", "")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        content = "".join(parts)

    content_text = str(content).strip()
    if not content_text:
        raise AIClientError("模型返回内容为空。")
    return content_text


def _parse_json_object(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AIClientError("模型返回不是有效 JSON。")
        try:
            payload = json.loads(content[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AIClientError("模型返回不是有效 JSON。") from exc

    if not isinstance(payload, dict):
        raise AIClientError("模型返回的顶层结构不是对象。")
    return payload
