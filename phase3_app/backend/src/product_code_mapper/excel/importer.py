from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from product_code_mapper.domain.models import CustomerItem


def import_customer_items(workbook_path: str | Path) -> list[CustomerItem]:
    workbook = load_workbook(Path(workbook_path), read_only=True, data_only=True)
    worksheet = workbook.active
    rows = worksheet.iter_rows(values_only=True)

    headers = [_clean_cell(value) for value in next(rows)]
    items: list[CustomerItem] = []

    for row_index, row in enumerate(rows, start=2):
        fields = {
            header: _clean_cell(value)
            for header, value in zip(headers, row, strict=False)
            if header
        }
        if _is_empty_row(fields):
            continue
        items.append(
            CustomerItem(
                row_id=f"row-{row_index}",
                original_row_index=row_index,
                fields=fields,
            )
        )

    workbook.close()
    return items


def _clean_cell(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _is_empty_row(fields: dict[str, str]) -> bool:
    return not any(value for value in fields.values())

