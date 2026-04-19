from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher.services.model_settings import (  # noqa: E402
    ModelSettingsError,
    load_model_settings,
    resolve_runtime_settings,
)
from product_matcher_phase2.batch_runner import (  # noqa: E402
    run_phase2_batch,
    summarize_batch_results,
    write_phase2_batch_results_xlsx,
)
from product_matcher_phase2.excel_loader import load_company_products, load_customer_records  # noqa: E402
from product_matcher_phase2.model_trial_runner import build_chat_json_model_caller  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run phase-2 batch coding against real Excel libraries.")
    parser.add_argument(
        "--customer",
        default=str(ROOT / "客户商品库.xlsx"),
        help="Path to the customer product library Excel file.",
    )
    parser.add_argument(
        "--company",
        default=str(ROOT / "我司商品库.xlsx"),
        help="Path to the company product library Excel file.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "runtime_data" / "exports" / "phase2_batch_results.xlsx"),
        help="Path to write phase-2 batch Excel results.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of customer rows to run. Leave unset to run all rows.",
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=10,
        help="Maximum number of candidate products sent to the model for each customer row.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        runtime_settings = resolve_runtime_settings(load_model_settings())
    except ModelSettingsError as exc:
        print(f"模型配置不可用：{exc}", file=sys.stderr)
        return 2

    customer_records = load_customer_records(args.customer)
    company_products = load_company_products(args.company)
    caller = build_chat_json_model_caller(runtime_settings)
    rows = run_phase2_batch(
        customer_records,
        company_products,
        caller,
        candidate_limit=args.candidate_limit,
        max_rows=args.limit,
    )
    write_phase2_batch_results_xlsx(rows, args.output)
    summary = summarize_batch_results(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"结果已写入：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
