from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook

from product_code_mapper.domain.models import CustomerItem, MatchResult
from product_code_mapper.domain.statuses import MatchStatus
from product_code_mapper.runs.engine import MatchRunResult


APPENDED_RESULT_HEADERS = [
    "对照状态",
    "我司商品编码",
    "我司商品名称",
    "我司品牌",
    "我司规格",
    "我司单位",
    "推荐理由",
    "证据对齐摘要",
    "风险提示",
    "备选候选",
    "是否需要人工审核",
    "人工确认结果",
    "人工审核备注",
]


def export_run_result(result: MatchRunResult, output_path: str | Path) -> None:
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "对照结果总表"
    evidence_sheet = workbook.create_sheet("详细证据表")
    metrics_sheet = workbook.create_sheet("统计汇总表")

    _write_summary_sheet(summary_sheet, result)
    _write_evidence_sheet(evidence_sheet, result)
    _write_metrics_sheet(metrics_sheet, result)

    workbook.save(Path(output_path))


def _write_summary_sheet(sheet, result: MatchRunResult) -> None:
    customer_headers = _customer_headers(result.customer_items)
    sheet.append(customer_headers + APPENDED_RESULT_HEADERS)

    results_by_row_id = {row_result.row_id: row_result for row_result in result.row_results}
    for item in result.customer_items:
        row_result = results_by_row_id.get(item.row_id)
        sheet.append(
            [item.fields.get(header, "") for header in customer_headers]
            + _result_values(row_result)
        )


def _write_evidence_sheet(sheet, result: MatchRunResult) -> None:
    sheet.append(["任务行ID", "对照状态", "推荐理由", "证据对齐摘要", "风险提示"])
    for row_result in result.row_results:
        sheet.append(
            [
                row_result.row_id,
                row_result.status.value,
                row_result.reason_summary,
                row_result.evidence_summary,
                row_result.risk_summary,
            ]
        )


def _write_metrics_sheet(sheet, result: MatchRunResult) -> None:
    metrics = result.metrics
    sheet.append(["指标", "数量"])
    sheet.append(["总客户行数", metrics.total_count])
    sheet.append(["自动落码", metrics.auto_code_count])
    sheet.append(["回到大自然池", metrics.returned_to_nature_count])
    sheet.append(["疑难池", metrics.hard_case_count])


def _customer_headers(customer_items: list[CustomerItem]) -> list[str]:
    headers: list[str] = []
    for item in customer_items:
        for header in item.fields:
            if header not in headers:
                headers.append(header)
    return headers


def _result_values(row_result: MatchResult | None) -> list[Any]:
    if row_result is None:
        return [""] * len(APPENDED_RESULT_HEADERS)

    product = row_result.selected_candidate.product if row_result.selected_candidate else None
    return [
        row_result.status.value,
        product.code if product else "",
        product.name if product else "",
        product.brand if product else "",
        product.spec if product else "",
        product.unit if product else "",
        row_result.reason_summary,
        row_result.evidence_summary,
        row_result.risk_summary,
        "",
        _needs_review(row_result.status),
        "",
        "",
    ]


def _needs_review(status: MatchStatus) -> str:
    if status in {MatchStatus.AUTO_CODE, MatchStatus.AUTO_CODE_WITH_DIFFERENCE}:
        return "否"
    return "是"

