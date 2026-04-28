from __future__ import annotations

import argparse
import os
from json import dumps as json_dumps
from pathlib import Path

from product_code_mapper.model.client import ModelClient
from product_code_mapper.validation.sample_runner import run_sample_validation


def main() -> int:
    parser = argparse.ArgumentParser(description="运行三期 3.1 DeepSeek 小批量真实样本验证")
    parser.add_argument("--company-xlsx", required=True, help="我司商品库 Excel 路径")
    parser.add_argument("--customer-xlsx", required=True, help="客户商品库 Excel 路径")
    parser.add_argument("--output-xlsx", required=True, help="验证结果导出路径")
    parser.add_argument("--limit", type=int, default=20, help="客户库验证行数，默认 20")
    parser.add_argument(
        "--customer-keyword",
        action="append",
        default=[],
        help="只验证包含该关键词的客户行，可重复传入，例如 --customer-keyword 生抽 --customer-keyword 酱油",
    )
    parser.add_argument("--base-url", default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    parser.add_argument("--model", default=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    args = parser.parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("缺少环境变量 DEEPSEEK_API_KEY。请先在当前 PowerShell 会话中设置，不要写入代码。")

    summary = run_sample_validation(
        company_path=Path(args.company_xlsx),
        customer_path=Path(args.customer_xlsx),
        output_path=Path(args.output_xlsx),
        model_client=ModelClient(
            base_url=args.base_url,
            api_key=api_key,
            model_name=args.model,
        ),
        limit=args.limit,
        customer_keywords=args.customer_keyword,
    )
    print(json_dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
