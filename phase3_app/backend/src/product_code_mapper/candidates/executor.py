from __future__ import annotations

from rapidfuzz import fuzz as _fuzz

from product_code_mapper.domain.models import Candidate, CompanyProduct, CustomerItem
from product_code_mapper.planning.round_command import RoundCommand

# Scoring weights aligned with 003 plan: core name > brand > spec > unit > package
WEIGHT_TERM_MATCH = 50
WEIGHT_BRAND = 20
WEIGHT_SPEC = 15
WEIGHT_NAME_CONTAINS = 12
WEIGHT_UNIT = 10
WEIGHT_PACKAGE = 8
WEIGHT_FUZZY_BONUS = 10
WEIGHT_LEXICON_BOOST = 15

FUZZY_SIMILARITY_THRESHOLD = 0.72


class CandidateExecutor:
    def __init__(self, products: list[CompanyProduct]) -> None:
        self._products = products

    def find_candidates(
        self,
        customer: CustomerItem,
        command: RoundCommand,
    ) -> list[Candidate]:
        scored = []
        for product in self._products:
            if _contains_any(product.identity_text, command.exclude_terms):
                continue
            candidate = self._score_product(product, customer, command)
            if candidate.score > 0:
                scored.append(candidate)

        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[: command.search_strategy.candidate_limit]

    def _score_product(
        self,
        product: CompanyProduct,
        customer: CustomerItem,
        command: RoundCommand,
    ) -> Candidate:
        customer_text = customer.display_text
        product_text = product.identity_text
        score = 0.0
        matched_terms: list[str] = []

        # Entry term matching
        all_entry_terms = command.entry_terms + command.entry_alias_terms
        for term in all_entry_terms:
            if term and term in product_text:
                score += WEIGHT_TERM_MATCH
                matched_terms.append(term)

        # Fuzzy matching for name
        customer_name = str(customer.fields.get("商品名称", "")).strip()
        if customer_name and product.name:
            fuzzy_ratio = _fuzz.partial_ratio(customer_name, product.name) / 100.0
            if fuzzy_ratio >= FUZZY_SIMILARITY_THRESHOLD:
                score += WEIGHT_FUZZY_BONUS
                matched_terms.append(f"模糊匹配:{product.name}")
            elif product.name in customer_text:
                score += WEIGHT_NAME_CONTAINS
                matched_terms.append(product.name)
        elif product.name and product.name in customer_text:
            score += WEIGHT_NAME_CONTAINS
            matched_terms.append(product.name)

        # Field-level matching
        for field_name, product_value, boost in [
            ("品牌", product.brand, WEIGHT_BRAND),
            ("规格", product.spec, WEIGHT_SPEC),
            ("单位", product.unit, WEIGHT_UNIT),
            ("包装", product.package, WEIGHT_PACKAGE),
        ]:
            if product_value and _field_matches_customer(customer, field_name, product_value):
                score += boost
                matched_terms.append(str(product_value))

        return Candidate(product=product, score=score, matched_terms=_deduplicate(matched_terms))


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term for term in terms if term and term in text)


def _field_matches_customer(customer: CustomerItem, field_name: str, product_value: str) -> bool:
    customer_value = str(customer.fields.get(field_name, "")).strip()
    if customer_value:
        if customer_value == product_value:
            return True
        if _fuzz.ratio(customer_value, product_value) >= 85:
            return True
        return False
    return product_value in customer.display_text


def _deduplicate(values: list[str]) -> list[str]:
    from product_code_mapper.utils import deduplicate
    return deduplicate(values)
