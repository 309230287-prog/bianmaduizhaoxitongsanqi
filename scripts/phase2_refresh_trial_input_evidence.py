from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher_phase2.candidate_generation import generate_candidates  # noqa: E402
from product_matcher_phase2.schemas import CandidateItem, CustomerRecord  # noqa: E402


def _refresh_row(row: dict[str, Any]) -> tuple[dict[str, Any], int]:
    refreshed = dict(row)
    payload = dict(refreshed.get("payload") or {})
    record = CustomerRecord.model_validate(payload.get("customer_record") or {})

    legacy_candidates = [
        CandidateItem.model_validate(candidate_payload)
        for candidate_payload in payload.get("candidate_products") or []
    ]
    refreshed_candidates = [
        candidate.model_dump(mode="json")
        for candidate in generate_candidates(
            record,
            [candidate.product for candidate in legacy_candidates],
            limit=len(legacy_candidates),
        )
    ]

    payload["candidate_products"] = refreshed_candidates
    refreshed["payload"] = payload
    return refreshed, len(refreshed_candidates)


def refresh_trial_input_evidence(input_path: str | Path, output_path: str | Path) -> dict[str, int]:
    source = Path(input_path)
    target = Path(output_path)
    rows = 0
    candidates = 0
    output_lines: list[str] = []

    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        refreshed_row, candidate_count = _refresh_row(json.loads(line))
        rows += 1
        candidates += candidate_count
        output_lines.append(json.dumps(refreshed_row, ensure_ascii=False, sort_keys=True))

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(output_lines) + ("\n" if output_lines else ""), encoding="utf-8")
    return {"rows": rows, "candidates": candidates}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh phase-2 trial JSONL with current candidate evidence.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "samples" / "phase2" / "model_trial_inputs_v0.1.jsonl"),
        help="Path to legacy phase-2 model trial JSONL inputs.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "samples" / "phase2" / "model_trial_inputs_v0.2.jsonl"),
        help="Path to write refreshed JSONL inputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = refresh_trial_input_evidence(args.input, args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"输入证据已刷新：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
