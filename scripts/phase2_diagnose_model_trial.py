from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.trial_diagnostics import (
    diagnose_trial_results_xlsx,
    render_trial_diagnostics_markdown,
)


DEFAULT_INPUT = Path("samples/phase2/model_trial_results_deepseek_v0.1.xlsx")
DEFAULT_OUTPUT = Path("samples/phase2/model_trial_diagnostics_deepseek_v0.1.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose Phase 2 model trial results offline.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    summary = diagnose_trial_results_xlsx(args.input)
    markdown = render_trial_diagnostics_markdown(summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
