from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from product_matcher_phase2.schemas import CandidateItem, CompanyProduct, CustomerRecord


SPEC_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?(?:ml|l|g|kg|毫升|升|克|千克)", re.IGNORECASE)
DOMAIN_SIGNAL_TERMS = [
    "可口可乐",
    "王老吉",
    "李锦记",
    "罗汉笋尖",
    "番茄沙司",
    "西红柿",
    "咸鸭蛋",
    "黄豆酱",
    "金标",
    "特级",
    "草菇",
    "生抽",
    "老抽",
    "番茄",
    "鸭蛋",
    "海天",
    "厨邦",
    "怡宝",
    "皮蛋",
    "咸蛋",
    "年糕",
]


@dataclass(frozen=True)
class _ScoredCandidate:
    score: int
    product: CompanyProduct
    sources: list[str]
    notes: list[str]


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[\s\[\]【】()（）{}<>《》,，。/\\_\-]+", "", normalized)


def _product_search_text(product: CompanyProduct) -> str:
    parts = [
        product.name,
        product.alias,
        product.description,
        " ".join(product.category_path),
        " ".join(product.raw_fields.values()),
    ]
    return _normalize(" ".join(part for part in parts if part))


def _spec_tokens(spec: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", spec).lower()
    return {_normalize(match.group(0)) for match in SPEC_TOKEN_RE.finditer(normalized)}


def _name_terms(name: str) -> list[str]:
    normalized_name = _normalize(name)
    return [
        normalized_term
        for term in DOMAIN_SIGNAL_TERMS
        if (normalized_term := _normalize(term)) and normalized_term in normalized_name
    ]


def _score_product(record: CustomerRecord, product: CompanyProduct) -> _ScoredCandidate | None:
    name = record.mapped_fields.get("name", "")
    spec = record.mapped_fields.get("spec", "")
    unit = record.mapped_fields.get("unit", "")
    normalized_name = _normalize(name)
    product_text = _product_search_text(product)
    normalized_product_name = _normalize(product.name)

    if not normalized_name:
        return None

    score = 0
    sources: list[str] = []
    notes: list[str] = []

    if normalized_name == normalized_product_name:
        score += 100
        sources.append("name_exact")
    elif normalized_name in product_text:
        score += 80
        sources.append("name_contains")
    elif (terms := _name_terms(name)) and all(term in product_text for term in terms):
        score += 70
        sources.append("name_terms_match")
    else:
        return None

    spec_hits = [token for token in _spec_tokens(spec) if token and token in product_text]
    if spec_hits:
        score += 40
        sources.append("spec_in_product_text")

    if unit and product.unit:
        if unit == product.unit:
            score += 10
            sources.append("unit_match")
        else:
            notes.append(f"单位不一致：客户={unit}，我司={product.unit}")

    return _ScoredCandidate(score=score, product=product, sources=sources, notes=notes)


def generate_candidates(
    record: CustomerRecord,
    products: Iterable[CompanyProduct],
    limit: int = 20,
) -> list[CandidateItem]:
    scored = [
        candidate
        for product in products
        if (candidate := _score_product(record, product)) is not None
    ]
    ranked = sorted(scored, key=lambda item: (-item.score, item.product.code, item.product.name))
    return [
        CandidateItem(
            candidate_id=f"K{index:06d}",
            product=item.product,
            candidate_sources=item.sources,
            candidate_notes="；".join(item.notes),
        )
        for index, item in enumerate(ranked[:limit], start=1)
    ]
