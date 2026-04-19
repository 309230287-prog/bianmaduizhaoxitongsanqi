from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from product_matcher.paths import RUNTIME_DIR


JOBS_DIR = RUNTIME_DIR / "jobs"
EXPORT_OUTPUT_DIR = RUNTIME_DIR / "exports"


def create_job(job_type: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    job_id = uuid4().hex
    payload = {
        "job_id": job_id,
        "job_type": job_type,
        "status": "queued",
        "progress": 0,
        "message": "任务已创建，等待开始。",
        "created_at": _now_text(),
        "updated_at": _now_text(),
        "metadata": metadata or {},
        "output_filename": "",
        "output_path": "",
        "error": "",
    }
    _write_job(payload)
    return payload


def load_job(job_id: str) -> dict[str, Any]:
    path = _job_file(job_id)
    if not path.exists():
        raise FileNotFoundError("未找到任务。")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def update_job(job_id: str, **fields: Any) -> dict[str, Any]:
    payload = load_job(job_id)
    payload.update(fields)
    payload["updated_at"] = _now_text()
    _write_job(payload)
    return payload


def save_job_output(job_id: str, filename: str, content: bytes) -> Path:
    EXPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_OUTPUT_DIR / f"{job_id}_{filename}"
    path.write_bytes(content)
    return path


def _write_job(payload: dict[str, Any]) -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    path = _job_file(payload["job_id"])
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(path)


def _job_file(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def _now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")
