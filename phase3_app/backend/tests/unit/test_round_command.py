import pytest

from product_code_mapper.planning.round_command import RoundCommand, RoundCommandValidationError


def valid_payload(**overrides):
    payload = {
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
    payload.update(overrides)
    return payload


def test_round_command_requires_exclude_terms():
    payload = valid_payload(exclude_terms=[])

    with pytest.raises(RoundCommandValidationError):
        RoundCommand.from_payload(payload)


def test_round_command_accepts_allowed_dimension():
    command = RoundCommand.from_payload(valid_payload())

    assert command.entry_dimension == "core_product_name"


def test_round_command_rejects_unknown_dimension():
    payload = valid_payload(entry_dimension="customer_category")

    with pytest.raises(RoundCommandValidationError):
        RoundCommand.from_payload(payload)


def test_round_command_requires_system_gate_policy():
    payload = valid_payload(auto_code_policy="model_decides")

    with pytest.raises(RoundCommandValidationError):
        RoundCommand.from_payload(payload)
