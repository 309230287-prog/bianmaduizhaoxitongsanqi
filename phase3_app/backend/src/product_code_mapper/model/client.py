"""Model client for calling OpenAI-compatible APIs (DeepSeek, Qwen, etc.)."""

from json import JSONDecodeError, loads as json_loads
from typing import Any

from httpx import Client, HTTPError, Timeout

from product_code_mapper.model.prompts import build_compare_prompt, build_round_plan_prompt
from product_code_mapper.model.schemas import (
    CompareResult,
    ModelOutputValidationError,
    validate_compare_payload,
)


class ModelClientError(Exception):
    """Raised when the model API call fails for any reason."""


class ModelClient:
    """HTTP client for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str = "deepseek-chat",
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        if not base_url.strip():
            raise ModelClientError("Base URL 未配置")
        if not api_key.strip():
            raise ModelClientError("API Key 未配置")
        if not model_name.strip():
            raise ModelClientError("模型名称未配置")

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._http: Client | None = None  # For test injection

    def plan_round(
        self,
        remaining_count: int,
        sample_items: list,
        completed_dimensions: list[str],
        round_no: int,
    ) -> dict[str, Any]:
        """Ask the model to plan the next processing round.

        Returns a raw payload dict suitable for RoundCommand.from_payload().
        """
        prompt = build_round_plan_prompt(remaining_count, sample_items, completed_dimensions, round_no)
        raw_json = self._chat(prompt)
        try:
            return json_loads(raw_json)
        except JSONDecodeError as exc:
            raise ModelClientError(f"模型输出不是合法 JSON: {exc}") from exc

    def compare(
        self,
        customer,
        candidates,
    ) -> CompareResult:
        """Ask the model to compare a customer item with candidates.

        Returns a validated CompareResult.
        """
        prompt = build_compare_prompt(customer, candidates)
        raw_json = self._chat(prompt)
        try:
            payload = json_loads(raw_json)
        except JSONDecodeError as exc:
            raise ModelClientError(f"模型比较输出不是合法 JSON: {exc}") from exc

        try:
            return validate_compare_payload(payload)
        except ModelOutputValidationError:
            raise

    def _chat(self, user_message: str) -> str:
        """Send a single-round chat completion request and return the message content."""
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 2):
            http = self._http
            close_http = http is None
            if http is None:
                http = Client(timeout=Timeout(self._timeout))
            try:
                response = http.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return _extract_json_block(str(content))
            except HTTPError as exc:
                last_error = exc
                if attempt <= self._max_retries:
                    continue
            except (KeyError, IndexError, TypeError) as exc:
                last_error = exc
                if attempt <= self._max_retries:
                    continue
            finally:
                if close_http and http is not None:
                    http.close()

        raise ModelClientError(
            f"模型调用失败（已重试 {self._max_retries} 次）: {last_error}"
        )


def _extract_json_block(text: str) -> str:
    """Extract the first JSON block from model output.

    Handles models that wrap JSON in markdown code fences.
    """
    text = text.strip()
    if "```" in text:
        lines = text.splitlines()
        collected: list[str] = []
        in_block = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_block:
                    break
                in_block = True
                continue
            if in_block:
                collected.append(line)
        if collected:
            return "\n".join(collected)
    # Try to find first { ... } as fallback
    brace_start = text.find("{")
    if brace_start >= 0:
        brace_end = text.rfind("}")
        if brace_end > brace_start:
            return text[brace_start : brace_end + 1]
    return text


class FakeModelClient:
    """Test double that returns hardcoded responses. Used in tests and demos."""

    def plan_round(
        self,
        remaining_items_summary: dict[str, Any] | None = None,
        *,
        remaining_count: int | None = None,
        sample_items: list | None = None,
        completed_dimensions: list[str] | None = None,
        round_no: int | None = None,
    ) -> dict[str, Any]:
        if remaining_items_summary is None:
            remaining_items_summary = {
                "sample_terms": _sample_terms_from_items(sample_items or []),
            }
        sample_terms = remaining_items_summary.get("sample_terms") or ["未分类商品"]
        entry_term = str(sample_terms[0]).strip() or "未分类商品"
        return {
            "round_id": "round_001",
            "round_name": f"核心品名_{entry_term}",
            "round_goal": f"集中处理包含 {entry_term} 共同特征的商品",
            "entry_dimension": "core_product_name",
            "entry_terms": [entry_term],
            "exclude_terms": _default_exclude_terms(entry_term),
            "must_check_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
            "hard_conflict_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
            "search_strategy": {
                "company_catalog_scope": "global",
                "candidate_limit": 20,
                "export_candidate_limit": 5,
            },
            "model_compare_policy": "compare_only_after_candidates",
            "auto_code_policy": "system_gate_required",
            "entry_alias_terms": [],
            "weak_related_terms": [],
        }

    def compare(self, customer, candidates) -> CompareResult:
        """Fake comparison that uses simple heuristics."""
        from product_code_mapper.domain.statuses import MatchStatus
        from product_code_mapper.model.schemas import CompareResult

        if not candidates:
            return CompareResult(
                selected_candidate_index=-1,
                status=MatchStatus.NO_RELIABLE_MATCH.value,
                reason_summary="无候选可供比较",
                evidence_summary="",
                risk_summary="",
                need_manual_review=True,
            )

        best = candidates[0]
        customer_text = customer.display_text
        if best.product.name in customer_text:
            return CompareResult(
                selected_candidate_index=0,
                status=MatchStatus.AUTO_CODE.value,
                reason_summary="品名一致，候选匹配",
                evidence_summary=f"客户商品包含候选品名: {best.product.name}",
                risk_summary="",
                matched_signals=["品名"],
                unmatched_signals=[],
                conflict_signals=[],
                need_manual_review=False,
            )

        return CompareResult(
            selected_candidate_index=0,
            status=MatchStatus.SUGGESTED_REVIEW.value,
            reason_summary="候选相似但无明确证据",
            evidence_summary="",
            risk_summary="品名不完全一致",
            matched_signals=[],
            unmatched_signals=["品名"],
            conflict_signals=[],
            need_manual_review=True,
        )


def _default_exclude_terms(entry_term: str) -> list[str]:
    if entry_term == "生抽":
        return ["老抽"]
    if entry_term == "老抽":
        return ["生抽"]
    return ["明显非同类商品"]


def _sample_terms_from_items(sample_items: list) -> list[str]:
    display_texts = [str(getattr(item, "display_text", "")) for item in sample_items]
    for marker in ["生抽", "老抽", "番茄", "酱油", "醋", "料酒", "蚝油"]:
        if any(marker in text for text in display_texts):
            return [marker]
    for item in sample_items:
        fields = getattr(item, "fields", {})
        name = str(fields.get("商品名称", "")).strip()
        if name:
            return [name]
    return ["未分类商品"]
