from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher

from product_matcher.models import MatchCandidate, MatchResult, NormalizedRecord


SAME_LEVEL_UNITS = {
    ("个", "只"),
    ("只", "个"),
    ("瓶", "支"),
    ("支", "瓶"),
}
RECALL_LIMIT = 80
TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")


def build_match_preview(
    customer_records: list[NormalizedRecord],
    company_records: list[NormalizedRecord],
    candidate_limit: int = 3,
) -> list[MatchResult]:
    index = _build_company_index(company_records)
    results: list[MatchResult] = []
    for customer in customer_records:
        candidates = _score_candidates(customer, company_records, index, candidate_limit)
        if not candidates:
            results.append(
                MatchResult(
                    customer_row_no=customer.row_no,
                    customer_name=customer.source_name,
                    customer_brand=customer.parsed_brand,
                    customer_spec=customer.parsed_spec,
                    customer_unit=customer.parsed_unit,
                    customer_category=customer.parsed_category,
                    match_status="unmatched",
                    top_score=0.0,
                    summary="没有召回到合理候选",
                    candidates=[],
                )
            )
            continue

        top = candidates[0]
        results.append(
            MatchResult(
                customer_row_no=customer.row_no,
                customer_name=customer.source_name,
                customer_brand=customer.parsed_brand,
                customer_spec=customer.parsed_spec,
                customer_unit=customer.parsed_unit,
                customer_category=customer.parsed_category,
                match_status=_grade_result(top),
                top_score=top.score,
                summary="；".join(top.reasons[:3]) or "已生成候选",
                candidates=candidates,
            )
        )
    return results


def _build_company_index(company_records: list[NormalizedRecord]) -> dict[str, dict[str, list[NormalizedRecord]]]:
    token_index: dict[str, list[NormalizedRecord]] = defaultdict(list)
    category_index: dict[str, list[NormalizedRecord]] = defaultdict(list)
    brand_index: dict[str, list[NormalizedRecord]] = defaultdict(list)

    for company in company_records:
        for token in _tokenize(company.parsed_name or company.cleaned_name):
            token_index[token].append(company)
        if company.parsed_category:
            category_index[company.parsed_category].append(company)
        if company.parsed_brand:
            brand_index[company.parsed_brand].append(company)

    return {
        "token": token_index,
        "category": category_index,
        "brand": brand_index,
    }


def _score_candidates(
    customer: NormalizedRecord,
    company_records: list[NormalizedRecord],
    index: dict[str, dict[str, list[NormalizedRecord]]],
    candidate_limit: int,
) -> list[MatchCandidate]:
    recall_pool = _recall_candidates(customer, company_records, index)
    scored: list[MatchCandidate] = []
    for company in recall_pool:
        candidate = _score_pair(customer, company)
        if candidate is not None:
            scored.append(candidate)
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:candidate_limit]


def _recall_candidates(
    customer: NormalizedRecord,
    company_records: list[NormalizedRecord],
    index: dict[str, dict[str, list[NormalizedRecord]]],
) -> list[NormalizedRecord]:
    recalled: list[NormalizedRecord] = []
    seen_ids: set[int] = set()

    def add(records: list[NormalizedRecord]) -> None:
        for record in records:
            identity = id(record)
            if identity in seen_ids:
                continue
            seen_ids.add(identity)
            recalled.append(record)
            if len(recalled) >= RECALL_LIMIT:
                return

    if customer.parsed_brand:
        add(index["brand"].get(customer.parsed_brand, []))
        if len(recalled) >= RECALL_LIMIT:
            return recalled

    for token in _tokenize(customer.parsed_name or customer.cleaned_name):
        add(index["token"].get(token, []))
        if len(recalled) >= RECALL_LIMIT:
            return recalled

    if customer.parsed_category:
        add(index["category"].get(customer.parsed_category, []))
        if len(recalled) >= RECALL_LIMIT:
            return recalled

    add(company_records[:RECALL_LIMIT])
    return recalled


def _score_pair(customer: NormalizedRecord, company: NormalizedRecord) -> MatchCandidate | None:
    reasons: list[str] = []
    hard_conflicts: list[str] = []

    name_score = _name_similarity(customer.parsed_name or customer.cleaned_name, company.parsed_name or company.cleaned_name)
    if name_score < 0.18:
        return None

    score = round(name_score * 60, 2)
    reasons.append(f"名称相似度 {name_score:.2f}")

    if customer.parsed_brand and company.parsed_brand:
        if customer.parsed_brand == company.parsed_brand:
            score += 18
            reasons.append("品牌一致")
        else:
            hard_conflicts.append("品牌冲突")
    elif customer.parsed_brand or company.parsed_brand:
        reasons.append("品牌信息不完整")

    if customer.parsed_spec and company.parsed_spec:
        if customer.parsed_spec == company.parsed_spec:
            score += 15
            reasons.append("规格一致")
        else:
            hard_conflicts.append("规格冲突")
    elif customer.parsed_spec or company.parsed_spec:
        reasons.append("规格信息不完整")

    if customer.parsed_unit and company.parsed_unit:
        if customer.parsed_unit == company.parsed_unit:
            score += 8
            reasons.append("单位一致")
        elif (customer.parsed_unit, company.parsed_unit) in SAME_LEVEL_UNITS:
            score += 4
            reasons.append("单位近似")
        else:
            hard_conflicts.append("单位层级冲突")
    elif customer.parsed_unit or company.parsed_unit:
        reasons.append("单位信息不完整")

    if customer.parsed_category and company.parsed_category:
        if customer.parsed_category == company.parsed_category:
            score += 6
            reasons.append("分类一致")
        else:
            score -= 4
            reasons.append("分类不一致")

    status = "candidate"
    if hard_conflicts:
        status = "hard_conflict"
        score -= 30
        reasons.extend(hard_conflicts)

    return MatchCandidate(
        company_row_no=company.row_no,
        company_code=company.source_code,
        company_name=company.source_name,
        company_brand=company.parsed_brand,
        company_spec=company.parsed_spec,
        company_unit=company.parsed_unit,
        company_category=company.parsed_category,
        score=max(round(score, 2), 0.0),
        status=status,
        reasons=reasons,
    )


def _grade_result(candidate: MatchCandidate) -> str:
    name_similarity = _extract_name_similarity(candidate.reasons)
    has_incomplete_signal = any("信息不完整" in reason for reason in candidate.reasons)
    if candidate.status == "hard_conflict":
        return "manual_review"
    if candidate.score >= 88 and name_similarity >= 0.85 and not has_incomplete_signal:
        return "auto_matched"
    if candidate.score >= 70:
        return "suggested"
    if candidate.score <= 0:
        return "unmatched"
    return "manual_review"


def _extract_name_similarity(reasons: list[str]) -> float:
    for reason in reasons:
        if not reason.startswith("名称相似度 "):
            continue
        try:
            return float(reason.split(" ", 1)[1])
        except (IndexError, ValueError):
            return 0.0
    return 0.0


def _name_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    ratio = SequenceMatcher(None, left, right).ratio()
    if left in right or right in left:
        ratio += 0.12
    overlap = len(set(left) & set(right)) / max(len(set(left)), 1)
    return min(max((ratio + overlap) / 2, 0.0), 1.0)


def _tokenize(value: str) -> list[str]:
    tokens: list[str] = []
    for chunk in TOKEN_RE.findall(value or ""):
        normalized = chunk.strip().lower()
        if not normalized:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", normalized) and len(normalized) >= 2:
            tokens.extend(normalized[index:index + 2] for index in range(len(normalized) - 1))
        else:
            tokens.append(normalized)
    return list(dict.fromkeys(tokens))
