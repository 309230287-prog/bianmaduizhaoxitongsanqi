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
from product_matcher_phase2.model_trial_runner import (  # noqa: E402
    build_chat_json_model_caller,
    run_trial_from_files,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run phase-2 model trial inputs.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "samples" / "phase2" / "model_trial_inputs_v0.1.jsonl"),
        help="Path to phase-2 model trial JSONL inputs.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "samples" / "phase2" / "model_trial_results_v0.1.xlsx"),
        help="Path to write model trial Excel results.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        runtime_settings = resolve_runtime_settings(load_model_settings())
    except ModelSettingsError as exc:
        print(f"模型配置不可用：{exc}", file=sys.stderr)
        return 2

    caller = build_chat_json_model_caller(runtime_settings)
    summary = run_trial_from_files(args.input, args.output, caller)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"结果已写入：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
