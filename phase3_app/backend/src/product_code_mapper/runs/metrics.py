from dataclasses import dataclass


@dataclass(frozen=True)
class RunMetrics:
    total_count: int
    auto_code_count: int
    auto_code_with_diff_count: int = 0
    suggested_review_count: int = 0
    manual_review_count: int = 0
    no_reliable_match_count: int = 0
    returned_to_nature_count: int = 0
    hard_case_count: int = 0
    total_rounds: int = 0
