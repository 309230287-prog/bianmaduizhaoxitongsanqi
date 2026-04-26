from __future__ import annotations

from product_code_mapper.domain.models import Candidate, CompanyProduct, CustomerItem
from product_code_mapper.planning.round_command import RoundCommand


class CandidateExecutor:
    def __init__(self, products: list[CompanyProduct]) -> None:
        self._products = products

    def find_candidates(
        self,
        customer: CustomerItem,
        command: RoundCommand,
    ) -> list[Candidate]:
        scored_candidates = [
            candidate
            for product in self._products
            if not _contains_any(product.identity_text, command.exclude_terms)
            if (candidate := self._score_product(product, customer, command)).score > 0
        ]
        return sorted(scored_candidates, key=lambda candidate: candidate.score, reverse=True)[
            : command.search_strategy.candidate_limit
        ]

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

        for term in command.entry_terms + command.entry_alias_terms:
            if term and (term in customer_text or term in product_text):
                score += 50
                matched_terms.append(term)

        for field_name, product_value, boost in [
            ("品牌", product.brand, 20),
            ("规格", product.spec, 15),
            ("单位", product.unit, 10),
            ("包装", product.package, 8),
        ]:
            if product_value and _field_matches_customer(customer, field_name, product_value):
                score += boost
                matched_terms.append(str(product_value))

        if product.name and product.name in customer_text:
            score += 12
            matched_terms.append(product.name)

        return Candidate(product=product, score=score, matched_terms=_deduplicate(matched_terms))


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term for term in terms if term and term in text)


def _field_matches_customer(customer: CustomerItem, field_name: str, product_value: str) -> bool:
    explicit_value = str(customer.fields.get(field_name, "")).strip()
    if explicit_value:
        return explicit_value == product_value
    return product_value in customer.display_text


def _deduplicate(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result

