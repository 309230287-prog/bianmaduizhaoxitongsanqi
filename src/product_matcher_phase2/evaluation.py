from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from product_matcher_phase2.schemas import CandidateItem


@dataclass(frozen=True)
class CandidateCoverageCase:
    sample_id: str
    expected_company_code: str
    candidates: Sequence[CandidateItem]


@dataclass(frozen=True)
class MissedCandidateCase:
    sample_id: str
    expected_company_code: str
    candidate_codes: list[str]


@dataclass(frozen=True)
class CandidateCoverageReport:
    evaluated_count: int
    topn_hits: dict[int, int]
    topn_coverage: dict[int, float]
    missed_cases: list[MissedCandidateCase]


def calculate_candidate_coverage(
    cases: Sequence[CandidateCoverageCase],
    top_n_values: Sequence[int] = (10, 20),
) -> CandidateCoverageReport:
    evaluated_cases = [case for case in cases if case.expected_company_code]
    evaluated_count = len(evaluated_cases)
    sorted_top_n = sorted(set(top_n_values))
    topn_hits = {top_n: 0 for top_n in sorted_top_n}
    missed_cases: list[MissedCandidateCase] = []
    largest_top_n = sorted_top_n[-1] if sorted_top_n else 0

    for case in evaluated_cases:
        candidate_codes = [candidate.product.code for candidate in case.candidates]
        for top_n in sorted_top_n:
            if case.expected_company_code in candidate_codes[:top_n]:
                topn_hits[top_n] += 1

        if case.expected_company_code not in candidate_codes[:largest_top_n]:
            missed_cases.append(
                MissedCandidateCase(
                    sample_id=case.sample_id,
                    expected_company_code=case.expected_company_code,
                    candidate_codes=candidate_codes[:largest_top_n],
                )
            )

    topn_coverage = {
        top_n: (hits / evaluated_count if evaluated_count else 0.0)
        for top_n, hits in topn_hits.items()
    }
    return CandidateCoverageReport(
        evaluated_count=evaluated_count,
        topn_hits=topn_hits,
        topn_coverage=topn_coverage,
        missed_cases=missed_cases,
    )
