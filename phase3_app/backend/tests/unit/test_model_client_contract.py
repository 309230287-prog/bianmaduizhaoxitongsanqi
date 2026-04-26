from product_code_mapper.model.client import FakeModelClient
from product_code_mapper.planning.round_command import RoundCommand


def test_fake_model_returns_structured_round_command():
    client = FakeModelClient()

    payload = client.plan_round(remaining_items_summary={"sample_terms": ["生抽"]})
    command = RoundCommand.from_payload(payload)

    assert command.entry_dimension == "core_product_name"
    assert command.entry_terms == ["生抽"]
    assert command.exclude_terms
    assert command.auto_code_policy == "system_gate_required"

