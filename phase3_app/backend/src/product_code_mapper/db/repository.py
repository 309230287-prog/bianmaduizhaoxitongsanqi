"""Repository layer — bridges business logic and SQLite storage."""

from json import dumps as json_dumps, loads as json_loads
from pathlib import Path
from sqlite3 import Connection
from threading import RLock

from product_code_mapper.db.connection import connect_db, ensure_schema
from product_code_mapper.runs.engine import MatchRunResult


class SettingsRepo:
    """Persists non-sensitive settings to SQLite."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn
        self._lock = RLock()

    def get(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO app_settings(key, value, updated_at) VALUES (?, ?, datetime('now'))"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, value),
            )
            self._conn.commit()

    def load_all(self) -> dict[str, str]:
        rows = self._conn.execute("SELECT key, value FROM app_settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


class TaskRepo:
    """Persists match tasks, task rows, runs, and run results."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn
        self._lock = RLock()

    # ---- Tasks ----

    def insert_task(self, task_id: str, name: str, customer_file: str, catalog_version_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO match_tasks(task_id, task_name, customer_file_name, catalog_version_id, status)"
                " VALUES (?, ?, ?, ?, 'created')",
                (task_id, name, customer_file, catalog_version_id),
            )
            self._conn.commit()

    def update_task_status(self, task_id: str, status: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE match_tasks SET status = ?, updated_at = datetime('now') WHERE task_id = ?",
                (status, task_id),
            )
            self._conn.commit()

    def get_task(self, task_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM match_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_tasks(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                t.*,
                COUNT(r.task_row_id) AS customer_count,
                EXISTS (
                    SELECT 1
                    FROM task_runs tr
                    JOIN run_results rr ON rr.run_id = tr.run_id
                    WHERE tr.task_id = t.task_id AND tr.status = 'completed'
                ) AS has_completed_results
            FROM match_tasks t
            LEFT JOIN task_rows r ON r.task_id = t.task_id
            GROUP BY t.task_id
            ORDER BY t.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- Task Rows ----

    def insert_task_rows(self, rows: list[dict]) -> None:
        with self._lock:
            self._conn.executemany(
                "INSERT INTO task_rows(task_row_id, task_id, original_row_number, raw_row_json,"
                " customer_name, customer_spec, customer_unit, customer_brand, customer_note)"
                " VALUES (:task_row_id, :task_id, :original_row_number, :raw_row_json,"
                " :customer_name, :customer_spec, :customer_unit, :customer_brand, :customer_note)",
                rows,
            )
            self._conn.commit()

    def get_task_rows(self, task_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM task_rows WHERE task_id = ? ORDER BY original_row_number",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- Runs ----

    def insert_run(self, run_id: str, task_id: str, round_no: int, total_count: int) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO task_runs(run_id, task_id, round_no, total_count, status, started_at)"
                " VALUES (?, ?, ?, ?, 'running', datetime('now'))",
                (run_id, task_id, round_no, total_count),
            )
            self._conn.commit()

    def update_run_status(self, run_id: str, status: str, stopped_reason: str = "") -> None:
        with self._lock:
            if status in ("completed", "stopped", "failed"):
                self._conn.execute(
                    "UPDATE task_runs SET status = ?, finished_at = datetime('now'), stopped_reason = ? WHERE run_id = ?",
                    (status, stopped_reason, run_id),
                )
            else:
                self._conn.execute(
                    "UPDATE task_runs SET status = ? WHERE run_id = ?",
                    (status, run_id),
                )
            self._conn.commit()

    def update_run_progress(self, run_id: str, completed_count: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE task_runs SET completed_count = ? WHERE run_id = ?",
                (completed_count, run_id),
            )
            self._conn.commit()

    def update_run_metrics(self, run_id: str, metrics) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE task_runs SET auto_code_count = ?, manual_review_count = ?, no_match_count = ?,"
                " completed_count = ? WHERE run_id = ?",
                (metrics.auto_code_count, metrics.manual_review_count,
                 metrics.no_reliable_match_count, metrics.total_count, run_id),
            )
            self._conn.commit()

    def get_run(self, run_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM task_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_latest_run(self, task_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM task_runs WHERE task_id = ? ORDER BY round_no DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        return dict(row) if row else None

    # ---- Run Results ----

    def insert_run_results(self, run_id: str, match_run_result: MatchRunResult) -> None:
        rows = []
        for item in match_run_result.customer_items:
            result = match_run_result.row_results.get(item.row_id)
            if result is None:
                continue
            rows.append({
                "run_id": run_id,
                "task_row_id": item.row_id,
                "result_status": result.status.value,
                "need_manual_review": 1 if result.status.value in ("必须人工审核", "建议落码待确认") else 0,
                "selected_company_code": result.selected_candidate.product.code if result.selected_candidate else "",
                "selected_company_name": result.selected_candidate.product.name if result.selected_candidate else "",
                "reason_summary": result.reason_summary,
                "evidence_summary": result.evidence_summary,
                "risk_summary": result.risk_summary,
                "matched_signals_json": json_dumps(result.audit.get("matched_signals", []), ensure_ascii=False),
                "conflict_signals_json": json_dumps(result.audit.get("conflict_signals", []), ensure_ascii=False),
                "candidates_json": json_dumps(result.audit.get("candidate_summaries", []), ensure_ascii=False),
                "audit_json": json_dumps(result.audit, ensure_ascii=False),
            })
        if rows:
            with self._lock:
                self._conn.executemany(
                    "INSERT INTO run_results(run_id, task_row_id, result_status, need_manual_review,"
                    " selected_company_code, selected_company_name, reason_summary, evidence_summary,"
                    " risk_summary, matched_signals_json, conflict_signals_json, candidates_json, audit_json)"
                    " VALUES (:run_id, :task_row_id, :result_status, :need_manual_review,"
                    " :selected_company_code, :selected_company_name, :reason_summary, :evidence_summary,"
                    " :risk_summary, :matched_signals_json, :conflict_signals_json, :candidates_json, :audit_json)",
                    rows,
                )
                self._conn.commit()

    def get_run_results(self, run_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM run_results WHERE run_id = ? ORDER BY result_id",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- Company Products ----

    def replace_company_products(self, catalog_version_id: str, file_name: str, file_path: str,
                                 products: list[dict], file_hash: str) -> int:
        with self._lock:
            self._conn.execute("UPDATE company_catalog_versions SET is_current = 0")
            self._conn.execute(
                "INSERT INTO company_catalog_versions(catalog_version_id, file_name, file_path, row_count,"
                " column_count, file_hash, is_current) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (catalog_version_id, file_name, str(file_path), len(products), 0, file_hash),
            )
            self._conn.executemany(
                "INSERT INTO company_products(catalog_version_id, company_code, company_name, brand, spec,"
                " unit, package, raw_row_json, search_text)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        catalog_version_id,
                        p["code"], p["name"], p.get("brand", ""), p.get("spec", ""),
                        p.get("unit", ""), p.get("package", ""),
                        json_dumps(p.get("extra_fields", {}), ensure_ascii=False),
                        f"{p.get('brand', '')} {p['name']} {p.get('spec', '')} {p.get('unit', '')}",
                    )
                    for p in products
                ],
            )
            self._conn.commit()
        return len(products)

    def get_company_products(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM company_products WHERE catalog_version_id ="
            " (SELECT catalog_version_id FROM company_catalog_versions WHERE is_current = 1)"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_company_codes(self) -> frozenset[str]:
        rows = self._conn.execute(
            "SELECT company_code FROM company_products WHERE catalog_version_id ="
            " (SELECT catalog_version_id FROM company_catalog_versions WHERE is_current = 1)"
        ).fetchall()
        return frozenset(r["company_code"] for r in rows)

    # ---- Field Mappings ----

    def save_field_mappings(self, task_id: str, source: str,
                            mappings: list[dict]) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM field_mappings WHERE task_id = ? AND source = ?",
                (task_id, source),
            )
            for m in mappings:
                self._conn.execute(
                    "INSERT INTO field_mappings(task_id, source, business_field, column_name, column_index,"
                    " importance_level, confirmed_by_user)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (task_id, source, m["business_field"], m["column_name"],
                     m["column_index"], m.get("importance_level", "optional"),
                     m.get("confirmed_by_user", 0)),
                )
            self._conn.commit()

    def get_field_mappings(self, task_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM field_mappings WHERE task_id = ? ORDER BY mapping_id",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- Action Logs ----

    def log_action(self, action_type: str, target_type: str = "",
                   target_id: str = "", message: str = "", details: dict | None = None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO action_logs(action_type, target_type, target_id, message, details_json)"
                " VALUES (?, ?, ?, ?, ?)",
                (action_type, target_type, target_id, message,
                 json_dumps(details or {}, ensure_ascii=False)),
            )
            self._conn.commit()


def create_repos(db_path: str | Path) -> tuple[SettingsRepo, TaskRepo]:
    """Create a database connection and return initialized repositories."""
    conn = connect_db(db_path)
    ensure_schema(conn)
    return SettingsRepo(conn), TaskRepo(conn)


def _candidate_summary(selected) -> dict:
    if selected is None:
        return {}
    p = selected.product
    return {
        "code": p.code,
        "name": p.name,
        "brand": p.brand,
        "spec": p.spec,
        "unit": p.unit,
    }
