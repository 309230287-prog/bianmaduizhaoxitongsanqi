from dataclasses import dataclass
from typing import Any


ALLOWED_ENTRY_DIMENSIONS = {
    "core_product_name",
    "brand",
    "alias_synonym",
    "spec_unit",
    "package_form",
    "series_marker",
    "flavor_form",
    "hard_case",
}


class RoundCommandValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SearchStrategy:
    company_catalog_scope: str
    candidate_limit: int
    export_candidate_limit: int


@dataclass(frozen=True)
class RoundCommand:
    round_id: str
    round_name: str
    round_goal: str
    entry_dimension: str
    entry_terms: list[str]
    exclude_terms: list[str]
    must_check_fields: list[str]
    hard_conflict_fields: list[str]
    search_strategy: SearchStrategy
    model_compare_policy: str
    auto_code_policy: str
    entry_alias_terms: list[str]
    weak_related_terms: list[str]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RoundCommand":
        cls._validate_payload(payload)
        strategy = payload["search_strategy"]
        return cls(
            round_id=str(payload["round_id"]),
            round_name=str(payload["round_name"]),
            round_goal=str(payload["round_goal"]),
            entry_dimension=str(payload["entry_dimension"]),
            entry_terms=list(payload["entry_terms"]),
            exclude_terms=list(payload["exclude_terms"]),
            must_check_fields=list(payload["must_check_fields"]),
            hard_conflict_fields=list(payload["hard_conflict_fields"]),
            search_strategy=SearchStrategy(
                company_catalog_scope=str(strategy["company_catalog_scope"]),
                candidate_limit=int(strategy["candidate_limit"]),
                export_candidate_limit=int(strategy["export_candidate_limit"]),
            ),
            model_compare_policy=str(payload["model_compare_policy"]),
            auto_code_policy=str(payload["auto_code_policy"]),
            entry_alias_terms=list(payload.get("entry_alias_terms", [])),
            weak_related_terms=list(payload.get("weak_related_terms", [])),
        )

    @staticmethod
    def _validate_payload(payload: dict[str, Any]) -> None:
        required_fields = [
            "round_id",
            "round_name",
            "round_goal",
            "entry_dimension",
            "entry_terms",
            "exclude_terms",
            "must_check_fields",
            "hard_conflict_fields",
            "search_strategy",
            "model_compare_policy",
            "auto_code_policy",
        ]
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise RoundCommandValidationError(f"模型发令缺少必要字段: {', '.join(missing)}")

        if payload["entry_dimension"] not in ALLOWED_ENTRY_DIMENSIONS:
            raise RoundCommandValidationError("模型发令使用了未允许的入圈维度")

        if not payload["entry_terms"]:
            raise RoundCommandValidationError("模型发令必须包含入圈词")

        if not payload["exclude_terms"]:
            raise RoundCommandValidationError("模型发令必须包含排除词")

        if not payload["must_check_fields"]:
            raise RoundCommandValidationError("模型发令必须包含必须检查字段")

        if not payload["hard_conflict_fields"]:
            raise RoundCommandValidationError("模型发令必须包含硬冲突字段")

        if payload["auto_code_policy"] != "system_gate_required":
            raise RoundCommandValidationError("自动落码必须经过系统安全门")

        strategy = payload["search_strategy"]
        for field in ["company_catalog_scope", "candidate_limit", "export_candidate_limit"]:
            if field not in strategy:
                raise RoundCommandValidationError(f"检索策略缺少必要字段: {field}")

        if int(strategy["candidate_limit"]) <= 0:
            raise RoundCommandValidationError("候选数量上限必须大于 0")

        if int(strategy["export_candidate_limit"]) <= 0:
            raise RoundCommandValidationError("导出候选数量上限必须大于 0")
