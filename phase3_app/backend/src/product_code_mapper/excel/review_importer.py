"""Import human-processed Excel for the next round.

From the execution plan §11A and requirements doc FR-12B:
- Human-confirmed results must not be overwritten.
- Human-specified codes must exist in the current company catalog.
- Previously unmatched items can re-enter the nature pool after catalog updates.
- Conflicts must produce Chinese error messages, never silently accepted.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

from openpyxl import load_workbook

from product_code_mapper.domain.models import CustomerItem
from product_code_mapper.domain.statuses import MatchStatus

REQUIRED_REVIEW_COLUMNS = [
    "系统任务行ID",
    "人工确认结果",
]

REVIEW_RESULT_COLUMN = "人工确认结果"
REVIEW_NOTE_COLUMN = "人工审核备注"
CONFIRMED_VALUE = "已确认"
NO_MATCH_VALUE = "无匹配"


@dataclass
class ReviewImportResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    confirmed_count: int = 0
    modified_count: int = 0
    no_match_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


WorkbookSource = str | Path | BinaryIO


def import_reviewed_excel(
    workbook_path: WorkbookSource,
    company_codes: frozenset[str],
) -> ReviewImportResult:
    """Read a human-processed Excel and validate its contents.

    Returns a ReviewImportResult with parsed rows, counts, errors, and warnings.
    """
    wb = load_workbook(
        workbook_path if isinstance(workbook_path, (str, Path)) else workbook_path,
        read_only=True,
        data_only=True,
    )
    result = ReviewImportResult()

    if "对照结果总表" not in wb.sheetnames:
        result.errors.append("Excel 缺少'对照结果总表'工作表，请确认使用的是导出文件")
        wb.close()
        return result

    sheet = wb["对照结果总表"]
    rows_iter = sheet.iter_rows(values_only=True)

    try:
        headers = [_clean(v) for v in next(rows_iter)]
    except StopIteration:
        result.errors.append("对照结果总表没有表头行")
        wb.close()
        return result

    if "系统任务行ID" not in headers:
        result.errors.append("缺少'系统任务行ID'列，无法识别任务行")
        wb.close()
        return result

    task_row_id_idx = headers.index("系统任务行ID")
    review_result_idx = headers.index(REVIEW_RESULT_COLUMN) if REVIEW_RESULT_COLUMN in headers else -1
    review_note_idx = headers.index(REVIEW_NOTE_COLUMN) if REVIEW_NOTE_COLUMN in headers else -1

    # Find additional columns for human modifications
    manual_code_idx = _find_column(headers, ["人工指定编码", "我司商品编码"])
    confirm_idx = _find_column(headers, ["人工确认结果"])

    for row in rows_iter:
        if not row or all(v is None for v in row):
            continue

        task_row_id = _clean(row[task_row_id_idx]) if task_row_id_idx < len(row) else ""
        if not task_row_id:
            result.warnings.append(f"行缺少系统任务行ID，已跳过")
            continue

        review_result = _clean(row[review_result_idx]) if review_result_idx >= 0 and review_result_idx < len(row) else ""
        review_note = _clean(row[review_note_idx]) if review_note_idx >= 0 and review_note_idx < len(row) else ""

        row_data = {
            "task_row_id": task_row_id,
            "review_result": review_result,
            "review_note": review_note,
            "specified_code": _clean(row[manual_code_idx]) if manual_code_idx >= 0 and manual_code_idx < len(row) else "",
            "original_values": {str(h): _clean(row[i]) if i < len(row) else ""
                               for i, h in enumerate(headers)},
        }

        specified_code = row_data["specified_code"]
        if review_result and specified_code and specified_code not in company_codes:
            result.errors.append(
                f"行 {task_row_id}: 人工填写的我司编码 '{specified_code}' 不存在于当前我司商品库"
            )

        if review_result == CONFIRMED_VALUE:
            result.confirmed_count += 1
        elif review_result in (NO_MATCH_VALUE, "需新增"):
            result.no_match_count += 1
        elif review_result:
            # Human modified - check if they specified a code
            result.modified_count += 1

        result.rows.append(row_data)

    wb.close()
    return result


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _find_column(headers: list[str], names: list[str]) -> int:
    for name in names:
        if name in headers:
            return headers.index(name)
    return -1
