import hashlib
import sqlite3
from pathlib import Path
from uuid import uuid4

from product_code_mapper.db.connection import connect_db, ensure_schema
from product_code_mapper.db.repository import SettingsRepo, TaskRepo


def test_settings_repo_saves_and_loads(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = SettingsRepo(conn)

    repo.set("model_name", "deepseek-chat")
    repo.set("base_url", "https://api.deepseek.com")

    assert repo.get("model_name") == "deepseek-chat"
    assert repo.get("base_url") == "https://api.deepseek.com"
    assert repo.get("missing", "fallback") == "fallback"


def test_settings_repo_loads_all(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = SettingsRepo(conn)

    repo.set("a", "1")
    repo.set("b", "2")

    all_settings = repo.load_all()
    assert all_settings["a"] == "1"
    assert all_settings["b"] == "2"


def test_task_repo_inserts_and_gets_task(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = TaskRepo(conn)

    task_id = uuid4().hex
    repo.insert_task(task_id, "测试任务", "客户库.xlsx", "cat-v1")

    task = repo.get_task(task_id)
    assert task is not None
    assert task["task_name"] == "测试任务"
    assert task["status"] == "created"


def test_task_repo_updates_status(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = TaskRepo(conn)

    task_id = uuid4().hex
    repo.insert_task(task_id, "测试", "c.xlsx", "v1")
    repo.update_task_status(task_id, "completed")

    assert repo.get_task(task_id)["status"] == "completed"


def test_task_repo_inserts_and_gets_task_rows(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = TaskRepo(conn)

    task_id = uuid4().hex
    repo.insert_task(task_id, "测试", "c.xlsx", "v1")
    rows = [
        {
            "task_row_id": "row-1",
            "task_id": task_id,
            "original_row_number": 2,
            "raw_row_json": '{"商品名称":"生抽"}',
            "customer_name": "生抽",
            "customer_spec": "500ml",
            "customer_unit": "瓶",
            "customer_brand": "海天",
            "customer_note": "",
        }
    ]
    repo.insert_task_rows(rows)
    result = repo.get_task_rows(task_id)
    assert len(result) == 1
    assert result[0]["customer_name"] == "生抽"


def test_task_rows_are_unique_inside_a_task_not_across_all_tasks(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = TaskRepo(conn)

    first_task_id = uuid4().hex
    second_task_id = uuid4().hex
    repo.insert_task(first_task_id, "任务一", "c1.xlsx", "v1")
    repo.insert_task(second_task_id, "任务二", "c2.xlsx", "v1")

    for task_id, name in [(first_task_id, "生抽"), (second_task_id, "老抽")]:
        repo.insert_task_rows([
            {
                "task_row_id": "row-2",
                "task_id": task_id,
                "original_row_number": 2,
                "raw_row_json": "{}",
                "customer_name": name,
                "customer_spec": "500ml",
                "customer_unit": "瓶",
                "customer_brand": "海天",
                "customer_note": "",
            }
        ])

    assert repo.get_task_rows(first_task_id)[0]["customer_name"] == "生抽"
    assert repo.get_task_rows(second_task_id)[0]["customer_name"] == "老抽"


def test_old_global_task_row_primary_key_is_migrated(tmp_path: Path):
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE match_tasks (
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
        CREATE TABLE task_rows (
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
        """
    )
    conn.close()

    migrated = connect_db(db_path)
    ensure_schema(migrated)

    pk_columns = [
        row["name"]
        for row in sorted(
            migrated.execute("PRAGMA table_info(task_rows)").fetchall(),
            key=lambda item: item["pk"],
        )
        if row["pk"]
    ]
    assert pk_columns == ["task_id", "task_row_id"]


def test_task_repo_manages_runs(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = TaskRepo(conn)

    task_id = uuid4().hex
    repo.insert_task(task_id, "测试", "c.xlsx", "v1")
    run_id = uuid4().hex

    repo.insert_run(run_id, task_id, round_no=1, total_count=10)
    run = repo.get_run(run_id)
    assert run is not None
    assert run["status"] == "running"
    assert run["total_count"] == 10

    repo.update_run_status(run_id, "completed")
    run = repo.get_run(run_id)
    assert run is not None
    assert run["status"] == "completed"
    assert run["finished_at"] is not None


def test_task_repo_saves_field_mappings(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = TaskRepo(conn)

    task_id = uuid4().hex
    repo.insert_task(task_id, "测试", "c.xlsx", "v1")

    mappings = [
        {"business_field": "商品名称", "column_name": "品名", "column_index": 0, "importance_level": "required", "confirmed_by_user": 1},
        {"business_field": "规格", "column_name": "规格", "column_index": 1, "importance_level": "suggested", "confirmed_by_user": 1},
    ]
    repo.save_field_mappings(task_id, "customer", mappings)
    result = repo.get_field_mappings(task_id)
    assert len(result) == 2
    assert result[0]["business_field"] == "商品名称"


def test_task_repo_replaces_company_products(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = TaskRepo(conn)

    products = [
        {"code": "P1", "name": "海天金标生抽", "brand": "海天", "spec": "500ml", "unit": "瓶", "extra_fields": {}},
    ]
    file_hash = hashlib.sha256(b"test").hexdigest()

    count = repo.replace_company_products("cat-v1", "我司库.xlsx", "/tmp/我司库.xlsx", products, file_hash)
    assert count == 1

    loaded = repo.get_company_products()
    assert len(loaded) == 1
    assert loaded[0]["company_name"] == "海天金标生抽"

    codes = repo.get_company_codes()
    assert codes == frozenset(["P1"])


def test_task_repo_logs_actions(tmp_path: Path):
    conn = connect_db(tmp_path / "test.db")
    ensure_schema(conn)
    repo = TaskRepo(conn)

    repo.log_action("task_created", target_type="task", target_id="task-1", message="新建对照任务")
    repo.log_action("export", target_type="run", target_id="run-1", details={"sheets": 3})
