from dataclasses import dataclass


@dataclass(frozen=True)
class RunMetrics:
    total_count: int
    auto_code_count: int
    returned_to_nature_count: int
    hard_case_count: int

