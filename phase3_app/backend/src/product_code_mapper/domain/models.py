from dataclasses import dataclass, field
from typing import Any

from product_code_mapper.domain.statuses import MatchStatus


def _join_non_empty(values: list[Any]) -> str:
    return " ".join(str(value).strip() for value in values if str(value).strip())


@dataclass(frozen=True)
class CustomerItem:
    row_id: str
    original_row_index: int
    fields: dict[str, Any]

    @property
    def display_text(self) -> str:
        preferred_columns = ["商品名称", "品名", "名称", "品牌", "规格", "单位", "备注"]
        values = [self.fields[column] for column in preferred_columns if column in self.fields]
        return _join_non_empty(values)


@dataclass(frozen=True)
class CompanyProduct:
    code: str
    name: str
    brand: str = ""
    spec: str = ""
    unit: str = ""
    package: str = ""
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @property
    def identity_text(self) -> str:
        return _join_non_empty([self.brand, self.name, self.spec, self.unit, self.package])


@dataclass(frozen=True)
class Candidate:
    product: CompanyProduct
    score: float
    matched_terms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MatchResult:
    row_id: str
    status: MatchStatus
    selected_candidate: Candidate | None = None
    reason_summary: str = ""
    evidence_summary: str = ""
    risk_summary: str = ""
    audit: dict[str, Any] = field(default_factory=dict)
