from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from product_matcher.paths import RUNTIME_DIR


UPLOADS_DIR = RUNTIME_DIR / "uploads"
TEMPLATE_FILE = RUNTIME_DIR / "mapping_templates.json"


def create_upload_session(
    company_filename: str,
    company_content: bytes,
    customer_filename: str,
    customer_content: bytes,
) -> str:
    session_id = uuid.uuid4().hex
    session_dir = UPLOADS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    (session_dir / "company.xlsx").write_bytes(company_content)
    (session_dir / "customer.xlsx").write_bytes(customer_content)
    metadata = {
        "company_filename": company_filename,
        "customer_filename": customer_filename,
    }
    (session_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    return session_id


def load_upload_session(session_id: str) -> dict[str, Path | str]:
    session_dir = UPLOADS_DIR / session_id
    metadata_path = session_dir / "metadata.json"
    if not session_dir.exists() or not metadata_path.exists():
        raise FileNotFoundError("未找到上传会话，请重新上传文件。")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return {
        "session_dir": session_dir,
        "company_path": session_dir / "company.xlsx",
        "customer_path": session_dir / "customer.xlsx",
        "company_filename": metadata["company_filename"],
        "customer_filename": metadata["customer_filename"],
    }


def load_mapping_template(company_preview, customer_preview) -> tuple[dict[str, str], dict[str, str]] | None:
    template_store = _load_template_store()
    template_key = _build_template_key(company_preview, customer_preview)
    payload = template_store.get(template_key)
    if not payload:
        return None
    return payload.get("company_mapping", {}), payload.get("customer_mapping", {})


def save_mapping_template(
    company_preview,
    customer_preview,
    company_mapping: dict[str, str],
    customer_mapping: dict[str, str],
) -> None:
    template_store = _load_template_store()
    template_key = _build_template_key(company_preview, customer_preview)
    template_store[template_key] = {
        "company_signature": _build_signature(company_preview),
        "customer_signature": _build_signature(customer_preview),
        "company_mapping": company_mapping,
        "customer_mapping": customer_mapping,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    TEMPLATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_FILE.write_text(json.dumps(template_store, ensure_ascii=False, indent=2), encoding="utf-8")



def _load_template_store() -> dict[str, Any]:
    if not TEMPLATE_FILE.exists():
        return {}
    try:
        payload = json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}



def _build_template_key(company_preview, customer_preview) -> str:
    return f"{_build_signature(company_preview)}__{_build_signature(customer_preview)}"



def _build_signature(preview) -> str:
    parts: list[str] = []
    for column in getattr(preview, "columns", []):
        raw_header = getattr(column, "raw_header", "")
        parts.append(str(raw_header).strip())
    return "||".join(parts)
