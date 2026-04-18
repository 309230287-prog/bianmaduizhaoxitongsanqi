from dataclasses import dataclass, field
from typing import Any


STATUS_LABELS = {
    "auto_matched": "自动匹配",
    "suggested": "建议匹配",
    "manual_review": "待人工审核",
    "unmatched": "未匹配",
    "candidate": "候选",
    "hard_conflict": "硬冲突",
}


@dataclass(slots=True)
class ColumnOption:
    index: int
    raw_header: str
    label: str
    value_key: str


@dataclass(slots=True)
class WorkbookPreview:
    filename: str
    sheet_name: str
    total_rows: int
    columns: list[ColumnOption] = field(default_factory=list)
    sample_rows: list[list[str]] = field(default_factory=list)


@dataclass(slots=True)
class StandardField:
    key: str
    label: str
    required: bool
    description: str


@dataclass(slots=True)
class NormalizedRecord:
    source_type: str
    row_no: int
    source_code: str
    source_name: str
    source_brand: str
    source_spec: str
    source_unit: str
    source_category: str
    cleaned_name: str
    parsed_brand: str
    parsed_name: str
    parsed_spec: str
    parsed_unit: str
    parsed_category: str
    parse_notes: str


@dataclass(slots=True)
class MatchCandidate:
    company_row_no: int
    company_code: str
    company_name: str
    company_brand: str
    company_spec: str
    company_unit: str
    company_category: str
    score: float
    status: str
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MatchResult:
    customer_row_no: int
    customer_name: str
    customer_brand: str
    customer_spec: str
    customer_unit: str
    customer_category: str
    match_status: str
    top_score: float
    summary: str
    candidates: list[MatchCandidate] = field(default_factory=list)


STANDARD_FIELDS: list[StandardField] = [
    StandardField("product_code", "商品编码", False, "用于标识、回写和历史关系复用"),
    StandardField("product_name", "商品名称", True, "必选，是后续匹配的第一入口"),
    StandardField("brand", "品牌", False, "建议映射，后续做品牌词库识别"),
    StandardField("spec", "规格", False, "建议映射，后续做规格标准化"),
    StandardField("unit", "单位", False, "建议映射，后续做单位层级判断"),
    StandardField("category", "分类", False, "辅助筛选和辅助判断字段"),
]


def preview_to_dict(preview: WorkbookPreview) -> dict[str, Any]:
    return {
        "filename": preview.filename,
        "sheet_name": preview.sheet_name,
        "total_rows": preview.total_rows,
        "columns": [
            {
                "index": column.index,
                "raw_header": column.raw_header,
                "label": column.label,
                "value_key": column.value_key,
            }
            for column in preview.columns
        ],
        "sample_rows": preview.sample_rows,
    }


def normalized_records_to_dicts(records: list[NormalizedRecord]) -> list[dict[str, Any]]:
    return [
        {
            "source_type": record.source_type,
            "row_no": record.row_no,
            "source_code": record.source_code,
            "source_name": record.source_name,
            "source_brand": record.source_brand,
            "source_spec": record.source_spec,
            "source_unit": record.source_unit,
            "source_category": record.source_category,
            "cleaned_name": record.cleaned_name,
            "parsed_brand": record.parsed_brand,
            "parsed_name": record.parsed_name,
            "parsed_spec": record.parsed_spec,
            "parsed_unit": record.parsed_unit,
            "parsed_category": record.parsed_category,
            "parse_notes": record.parse_notes,
        }
        for record in records
    ]


def match_results_to_dicts(results: list[MatchResult]) -> list[dict[str, Any]]:
    return [
        {
            "customer_row_no": result.customer_row_no,
            "customer_name": result.customer_name,
            "customer_brand": result.customer_brand,
            "customer_spec": result.customer_spec,
            "customer_unit": result.customer_unit,
            "customer_category": result.customer_category,
            "match_status": result.match_status,
            "match_status_label": STATUS_LABELS.get(result.match_status, result.match_status),
            "top_score": result.top_score,
            "summary": result.summary,
            "candidates": [
                {
                    "company_row_no": candidate.company_row_no,
                    "company_code": candidate.company_code,
                    "company_name": candidate.company_name,
                    "company_brand": candidate.company_brand,
                    "company_spec": candidate.company_spec,
                    "company_unit": candidate.company_unit,
                    "company_category": candidate.company_category,
                    "score": candidate.score,
                    "status": candidate.status,
                    "status_label": STATUS_LABELS.get(candidate.status, candidate.status),
                    "reasons": candidate.reasons,
                }
                for candidate in result.candidates
            ],
        }
        for result in results
    ]