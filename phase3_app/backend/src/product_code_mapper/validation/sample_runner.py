from __future__ import annotations

from pathlib import Path
from typing import Any

from product_code_mapper.excel.exporter import export_run_result
from product_code_mapper.excel.importer import import_company_products, import_customer_items
from product_code_mapper.runs.engine import MatchRunEngine


def run_sample_validation(
    *,
    company_path: str | Path,
    customer_path: str | Path,
    output_path: str | Path,
    model_client,
    limit: int = 20,
    customer_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Run a small-batch validation using real Excel files and an injected model client."""
    products = import_company_products(company_path)
    customer_items = import_customer_items(customer_path)
    filtered_items = _filter_customer_items(customer_items, customer_keywords or [])
    selected_items = filtered_items[: max(limit, 1)]
    result = MatchRunEngine(model_client=model_client).run_full(selected_items, products)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    export_run_result(result, output)
    return {
        "total_count": result.metrics.total_count,
        "auto_code_count": result.metrics.auto_code_count,
        "suggested_review_count": result.metrics.suggested_review_count,
        "manual_review_count": result.metrics.manual_review_count,
        "no_reliable_match_count": result.metrics.no_reliable_match_count,
        "total_rounds": result.metrics.total_rounds,
        "output_path": str(output),
        "customer_keywords": [keyword for keyword in (customer_keywords or []) if keyword.strip()],
    }


def _filter_customer_items(customer_items, keywords: list[str]):
    normalized = [keyword.strip() for keyword in keywords if keyword.strip()]
    if not normalized:
        return customer_items
    return [
        item
        for item in customer_items
        if any(keyword in item.display_text for keyword in normalized)
    ]
