from product_code_mapper.knowledge.lexicon import (
    Lexicon,
    LexiconEntry,
    LexiconEntryStatus,
    LexiconEntryType,
)


def test_confirmed_strong_synonym_can_expand_terms():
    lexicon = Lexicon(
        [
            LexiconEntry(
                entry_type=LexiconEntryType.STRONG_SYNONYM,
                status=LexiconEntryStatus.CONFIRMED,
                terms=["番茄", "西红柿"],
            )
        ]
    )

    assert lexicon.expand_confirmed_terms("番茄") == {"番茄", "西红柿"}


def test_weak_related_term_cannot_support_auto_code():
    entry = LexiconEntry(
        entry_type=LexiconEntryType.WEAK_RELATED,
        status=LexiconEntryStatus.CONFIRMED,
        terms=["生抽", "酱油"],
    )

    assert not entry.can_support_auto_code


def test_suggested_entry_only_expands_for_search_not_auto_code():
    entry = LexiconEntry(
        entry_type=LexiconEntryType.STRONG_SYNONYM,
        status=LexiconEntryStatus.SUGGESTED,
        terms=["土豆", "马铃薯"],
    )

    assert not entry.can_support_auto_code
