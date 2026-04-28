"""Field confirmation — maps Excel columns to business field meanings.

From the requirements doc (FR-04, §12):
- Required fields: 客户商品名称 (customer), 我司商品编码 + 我司商品名称 (company)
- Suggested fields: 品牌, 规格, 单位, 备注, 分类
- Optional fields: 客户编号, table sequence numbers, etc.
- Non-participating: user can mark columns as irrelevant
"""

from dataclasses import dataclass, field
from typing import Any

BUSINESS_FIELDS = [
    "商品名称",
    "商品编码",
    "品牌",
    "规格",
    "单位",
    "包装",
    "类别",
    "备注",
    "描述",
    "别名",
    "编号",
    "不参与判断",
]

REQUIRED_CUSTOMER_FIELDS = {"商品名称"}
REQUIRED_COMPANY_FIELDS = {"商品编码", "商品名称"}
SUGGESTED_FIELDS = {"品牌", "规格", "单位", "备注", "类别", "包装", "描述"}


@dataclass(frozen=True)
class FieldMapping:
    business_field: str
    column_name: str
    column_index: int
    importance_level: str = "optional"  # required / suggested / optional / ignored
    confirmed_by_user: bool = False


class FieldConfirmationError(ValueError):
    pass


@dataclass
class FieldConfirmation:
    source: str  # "customer" or "company"
    mappings: list[FieldMapping] = field(default_factory=list)
    _confirmed: bool = False

    def confirm(self) -> None:
        self._confirmed = True

    @property
    def is_confirmed(self) -> bool:
        return self._confirmed

    def missing_required_fields(self) -> list[str]:
        mapped = {m.business_field for m in self.mappings if m.importance_level != "ignored"}
        if self.source == "customer":
            return sorted(REQUIRED_CUSTOMER_FIELDS - mapped)
        return sorted(REQUIRED_COMPANY_FIELDS - mapped)

    def missing_suggested_fields(self) -> list[str]:
        mapped = {m.business_field for m in self.mappings if m.importance_level != "ignored"}
        return sorted(SUGGESTED_FIELDS - mapped)

    def get_column_for(self, business_field: str) -> str | None:
        for m in self.mappings:
            if m.business_field == business_field and m.importance_level != "ignored":
                return m.column_name
        return None

    def active_mappings(self) -> list[FieldMapping]:
        return [m for m in self.mappings if m.importance_level != "ignored"]

    def to_dicts(self) -> list[dict[str, Any]]:
        return [
            {
                "business_field": m.business_field,
                "column_name": m.column_name,
                "column_index": m.column_index,
                "importance_level": m.importance_level,
                "confirmed_by_user": m.confirmed_by_user,
            }
            for m in self.mappings
        ]


def suggest_customer_mapping(headers: list[str]) -> FieldConfirmation:
    """Auto-suggest field mappings for customer Excel columns."""
    return _suggest_mapping("customer", headers, primary_lookups=[
        ("商品名称", ["商品名称", "品名", "名称", "商品名", "产品名称", "货品名称"]),
        ("品牌", ["品牌", "品牌名称", "商标"]),
        ("规格", ["规格", "规格型号", "包装规格", "产品规格"]),
        ("单位", ["单位", "计量单位", "销售单位"]),
        ("备注", ["备注", "说明", "补充说明", "标记"]),
        ("编号", ["编号", "客户编号", "商品编号", "货号"]),
        ("类别", ["类别", "分类", "商品类别", "品类"]),
    ])


def suggest_company_mapping(headers: list[str]) -> FieldConfirmation:
    """Auto-suggest field mappings for company catalog Excel columns."""
    return _suggest_mapping("company", headers, primary_lookups=[
        ("商品编码", ["商品编码", "编码", "SPUID", "spu_id", "产品编码"]),
        ("商品名称", ["商品名称", "商品名", "品名", "名称", "SPU名称", "产品名称"]),
        ("品牌", ["品牌", "品牌名称"]),
        ("规格", ["规格", "规格型号", "SPU描述"]),
        ("单位", ["单位", "计量单位"]),
        ("包装", ["包装", "包装单位"]),
        ("类别", ["类别", "分类", "商品类别"]),
        ("描述", ["描述", "商品描述", "说明"]),
        ("别名", ["别名", "俗称", "其他名称"]),
    ])


def _suggest_mapping(
    source: str,
    headers: list[str],
    primary_lookups: list[tuple[str, list[str]]],
) -> FieldConfirmation:
    mappings: list[FieldMapping] = []
    used_indices: set[int] = set()

    for business_field, lookup_names in primary_lookups:
        for idx, header in enumerate(headers):
            if idx in used_indices:
                continue
            clean = header.strip()
            if clean in lookup_names or any(lk in clean for lk in lookup_names):
                importance = "required" if _is_required(source, business_field) else (
                    "suggested" if business_field in SUGGESTED_FIELDS else "optional"
                )
                mappings.append(FieldMapping(
                    business_field=business_field,
                    column_name=clean,
                    column_index=idx,
                    importance_level=importance,
                ))
                used_indices.add(idx)
                break

    # Add remaining unmapped columns
    for idx, header in enumerate(headers):
        if idx not in used_indices:
            clean = header.strip()
            if clean:
                mappings.append(FieldMapping(
                    business_field="不参与判断",
                    column_name=clean,
                    column_index=idx,
                    importance_level="ignored",
                ))
    return FieldConfirmation(source=source, mappings=mappings)


def _is_required(source: str, business_field: str) -> bool:
    if source == "customer":
        return business_field in REQUIRED_CUSTOMER_FIELDS
    return business_field in REQUIRED_COMPANY_FIELDS
