from __future__ import annotations

from typing import Any


class FakeModelClient:
    def plan_round(self, remaining_items_summary: dict[str, Any]) -> dict[str, Any]:
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


def _default_exclude_terms(entry_term: str) -> list[str]:
    if entry_term == "生抽":
        return ["老抽"]
    if entry_term == "老抽":
        return ["生抽"]
    return ["明显非同类商品"]

