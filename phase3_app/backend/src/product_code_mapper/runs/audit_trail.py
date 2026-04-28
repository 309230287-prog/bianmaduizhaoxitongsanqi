from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    row_id: str
    event: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class AuditTrail:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def add(self, row_id: str, event: str, message: str, **details: Any) -> None:
        self._entries.append(
            AuditEntry(row_id=row_id, event=event, message=message, details=details)
        )

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)
