from dataclasses import dataclass
from enum import Enum


class LexiconEntryType(str, Enum):
    STRONG_SYNONYM = "强同义"
    REGIONAL_ALIAS = "地区别名"
    BRAND_ALIAS = "品牌别名"
    SPEC_EQUIVALENT = "规格等价"
    WEAK_RELATED = "弱相关"
    HIERARCHY = "上下位"
    SERIES_MARKER = "系列标识"
    FLAVOR_FORM = "口味形态"


class LexiconEntryStatus(str, Enum):
    SUGGESTED = "suggested"
    TRIAL = "trial"
    CONFIRMED = "confirmed"
    BLOCKED = "blocked"


AUTO_CODE_SUPPORT_TYPES = {
    LexiconEntryType.STRONG_SYNONYM,
    LexiconEntryType.REGIONAL_ALIAS,
    LexiconEntryType.BRAND_ALIAS,
    LexiconEntryType.SPEC_EQUIVALENT,
}


@dataclass(frozen=True)
class LexiconEntry:
    entry_type: LexiconEntryType
    status: LexiconEntryStatus
    terms: list[str]
    source: str = ""

    @property
    def can_support_auto_code(self) -> bool:
        return self.status == LexiconEntryStatus.CONFIRMED and self.entry_type in AUTO_CODE_SUPPORT_TYPES

    @property
    def can_expand_search(self) -> bool:
        return self.status in {LexiconEntryStatus.TRIAL, LexiconEntryStatus.CONFIRMED}


class Lexicon:
    def __init__(self, entries: list[LexiconEntry] | None = None) -> None:
        self._entries = entries or []

    def expand_confirmed_terms(self, term: str) -> set[str]:
        expanded = {term}
        for entry in self._entries:
            if entry.can_support_auto_code and term in entry.terms:
                expanded.update(entry.terms)
        return expanded

    def expand_search_terms(self, term: str) -> set[str]:
        expanded = {term}
        for entry in self._entries:
            if entry.can_expand_search and term in entry.terms:
                expanded.update(entry.terms)
        return expanded
