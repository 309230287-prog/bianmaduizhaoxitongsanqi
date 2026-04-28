"""Shared utilities used across modules."""


def deduplicate(values: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
