import json

import httpx
import pytest

from product_code_mapper.model.client import FakeModelClient, ModelClient, ModelClientError
from product_code_mapper.planning.round_command import RoundCommand


def test_fake_model_returns_structured_round_command():
    client = FakeModelClient()

    payload = client.plan_round(remaining_items_summary={"sample_terms": ["生抽"]})
    command = RoundCommand.from_payload(payload)

    assert command.entry_dimension == "core_product_name"
    assert command.entry_terms == ["生抽"]
    assert command.exclude_terms
    assert command.auto_code_policy == "system_gate_required"


def test_model_client_sends_correct_request():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" in request.headers
        payload = json.loads(request.content)
        assert payload["model"] == "deepseek-chat"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(_valid_round_command_payload(), ensure_ascii=False)
                        }
                    }
                ]
            },
        )

    client = ModelClient(
        base_url="https://api.deepseek.com",
        api_key="sk-test",
        model_name="deepseek-chat",
    )
    client._http = httpx.Client(transport=httpx.MockTransport(handler))

    payload = client.plan_round(
        remaining_count=5,
        sample_items=[],
        completed_dimensions=[],
        round_no=1,
    )
    command = RoundCommand.from_payload(payload)

    assert command.entry_terms == ["生抽"]
    assert command.auto_code_policy == "system_gate_required"


def test_model_client_rejects_malformed_json():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "不是JSON"}}]},
        )

    client = ModelClient(
        base_url="https://api.deepseek.com",
        api_key="sk-test",
        model_name="deepseek-chat",
    )
    client._http = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(ModelClientError, match="模型输出不是合法 JSON"):
        client.plan_round(
            remaining_count=5,
            sample_items=[],
            completed_dimensions=[],
            round_no=1,
        )


def _valid_round_command_payload() -> dict:
    return {
        "round_id": "round_001",
        "round_name": "核心品名_生抽",
        "round_goal": "处理生抽",
        "entry_dimension": "core_product_name",
        "entry_terms": ["生抽"],
        "exclude_terms": ["老抽"],
        "must_check_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
        "hard_conflict_fields": ["核心品名", "品牌", "规格", "单位", "包装"],
        "search_strategy": {
            "company_catalog_scope": "global",
            "candidate_limit": 20,
            "export_candidate_limit": 5,
        },
        "model_compare_policy": "compare_only_after_candidates",
        "auto_code_policy": "system_gate_required",
    }
