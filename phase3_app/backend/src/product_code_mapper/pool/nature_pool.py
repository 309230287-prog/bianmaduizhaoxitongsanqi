from dataclasses import dataclass
from typing import Iterable

from product_code_mapper.domain.models import CustomerItem


@dataclass(frozen=True)
class ReturnRecord:
    row_id: str
    dimension: str
    reason: str


class NaturePool:
    def __init__(
        self,
        items: Iterable[CustomerItem],
        *,
        max_rounds_per_item: int = 5,
        max_rounds_per_dimension: int = 2,
    ) -> None:
        self._items = {item.row_id: item for item in items}
        self._remaining_row_ids = set(self._items)
        self._hard_case_row_ids: set[str] = set()
        self._return_records: dict[str, list[ReturnRecord]] = {row_id: [] for row_id in self._items}
        self._max_rounds_per_item = max_rounds_per_item
        self._max_rounds_per_dimension = max_rounds_per_dimension

    @property
    def remaining_row_ids(self) -> set[str]:
        return set(self._remaining_row_ids)

    @property
    def hard_case_row_ids(self) -> set[str]:
        return set(self._hard_case_row_ids)

    def can_enter_dimension(self, row_id: str, dimension: str) -> bool:
        if row_id in self._hard_case_row_ids:
            return False
        if row_id not in self._remaining_row_ids:
            return False
        return self._dimension_return_count(row_id, dimension) < self._max_rounds_per_dimension

    def record_return(self, row_id: str, *, dimension: str, reason: str) -> None:
        self._ensure_known_row(row_id)
        self._remaining_row_ids.add(row_id)
        self._return_records[row_id].append(ReturnRecord(row_id=row_id, dimension=dimension, reason=reason))
        if len(self._return_records[row_id]) >= self._max_rounds_per_item:
            self._hard_case_row_ids.add(row_id)

    def mark_completed(self, row_id: str) -> None:
        self._ensure_known_row(row_id)
        self._remaining_row_ids.discard(row_id)

    def return_records_for(self, row_id: str) -> list[ReturnRecord]:
        self._ensure_known_row(row_id)
        return list(self._return_records[row_id])

    def _dimension_return_count(self, row_id: str, dimension: str) -> int:
        self._ensure_known_row(row_id)
        return sum(1 for record in self._return_records[row_id] if record.dimension == dimension)

    def _ensure_known_row(self, row_id: str) -> None:
        if row_id not in self._items:
            raise KeyError(f"未知客户商品行: {row_id}")
