from __future__ import annotations

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from product_matcher.paths import RUNTIME_DIR


LOG_DIR = RUNTIME_DIR / "logs"
APP_LOG_FILE = LOG_DIR / "app.log"
ACTION_LOG_FILE = LOG_DIR / "actions.jsonl"


def ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_runtime(level: str, message: str, **context: Any) -> None:
    ensure_log_dir()
    line = {
        "time": _timestamp(),
        "level": level.upper(),
        "message": message,
        "context": context,
    }
    with APP_LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(_format_runtime_line(line) + "\n")


def log_action(action_name: str, **context: Any) -> None:
    ensure_log_dir()
    payload = {
        "time": _timestamp(),
        "action": action_name,
        **context,
    }
    with ACTION_LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def log_exception(message: str, exc: Exception, **context: Any) -> None:
    log_runtime(
        "ERROR",
        message,
        error_type=exc.__class__.__name__,
        error=str(exc),
        traceback=traceback.format_exc(limit=8),
        **context,
    )



def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")



def _format_runtime_line(payload: dict[str, Any]) -> str:
    context = json.dumps(payload.get("context", {}), ensure_ascii=False)
    return f"{payload['time']} | {payload['level']} | {payload['message']} | {context}"
