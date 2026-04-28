"""SQLite connection management."""

from pathlib import Path
from sqlite3 import Connection, connect


def connect_db(db_path: str | Path) -> Connection:
    """Open a SQLite connection with WAL mode and foreign keys enabled.

    check_same_thread=False is required because FastAPI runs endpoint
    handlers in a thread pool, not the main thread.
    """
    conn = connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = lambda cursor, row: dict(
        (col[0], row[idx]) for idx, col in enumerate(cursor.description)
    )
    return conn


def ensure_schema(conn: Connection) -> None:
    """Create all tables if they don't exist."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS company_catalog_versions (
    catalog_version_id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_current INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS company_products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog_version_id TEXT NOT NULL REFERENCES company_catalog_versions(catalog_version_id),
    company_code TEXT NOT NULL,
    company_name TEXT NOT NULL,
    brand TEXT NOT NULL DEFAULT '',
    spec TEXT NOT NULL DEFAULT '',
    unit TEXT NOT NULL DEFAULT '',
    package TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    raw_row_json TEXT NOT NULL DEFAULT '{}',
    search_text TEXT NOT NULL DEFAULT '',
    imported_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS match_tasks (
    task_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'excel',
    customer_file_name TEXT NOT NULL DEFAULT '',
    customer_file_path TEXT NOT NULL DEFAULT '',
    catalog_version_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'created',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_rows (
    task_row_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES match_tasks(task_id),
    original_row_number INTEGER NOT NULL,
    raw_row_json TEXT NOT NULL DEFAULT '{}',
    customer_name TEXT NOT NULL DEFAULT '',
    customer_spec TEXT NOT NULL DEFAULT '',
    customer_unit TEXT NOT NULL DEFAULT '',
    customer_brand TEXT NOT NULL DEFAULT '',
    customer_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS field_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES match_tasks(task_id),
    source TEXT NOT NULL,
    business_field TEXT NOT NULL,
    column_name TEXT NOT NULL,
    column_index INTEGER NOT NULL,
    importance_level TEXT NOT NULL DEFAULT 'optional',
    confirmed_by_user INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_runs (
    run_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES match_tasks(task_id),
    round_no INTEGER NOT NULL DEFAULT 1,
    catalog_version_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'created',
    total_count INTEGER NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    auto_code_count INTEGER NOT NULL DEFAULT 0,
    manual_review_count INTEGER NOT NULL DEFAULT 0,
    no_match_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    finished_at TEXT,
    stopped_reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS run_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES task_runs(run_id),
    task_row_id TEXT NOT NULL,
    result_status TEXT NOT NULL DEFAULT '',
    need_manual_review INTEGER NOT NULL DEFAULT 0,
    selected_company_code TEXT NOT NULL DEFAULT '',
    selected_company_name TEXT NOT NULL DEFAULT '',
    reason_summary TEXT NOT NULL DEFAULT '',
    evidence_summary TEXT NOT NULL DEFAULT '',
    risk_summary TEXT NOT NULL DEFAULT '',
    matched_signals_json TEXT NOT NULL DEFAULT '[]',
    conflict_signals_json TEXT NOT NULL DEFAULT '[]',
    candidates_json TEXT NOT NULL DEFAULT '[]',
    audit_json TEXT NOT NULL DEFAULT '{}',
    model_trace_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS action_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    target_type TEXT NOT NULL DEFAULT '',
    target_id TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_company_products_code ON company_products(company_code);
CREATE INDEX IF NOT EXISTS idx_company_products_search ON company_products(search_text);
CREATE INDEX IF NOT EXISTS idx_task_rows_task ON task_rows(task_id);
CREATE INDEX IF NOT EXISTS idx_run_results_run ON run_results(run_id);
CREATE INDEX IF NOT EXISTS idx_task_runs_task ON task_runs(task_id);
"""
