from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_one_click_windows_launcher_exists_and_points_to_python_start_script() -> None:
    launcher = REPO_ROOT / "启动商品匹配系统.bat"

    assert launcher.exists()
    content = launcher.read_text(encoding="utf-8")

    assert "chcp 65001" in content
    assert "PYTHONUTF8=1" in content
    assert "PYTHONPATH=%APP_ROOT%src" in content
    assert "scripts\\start_app.py" in content


def test_python_start_script_opens_phase2_workbench_on_default_port() -> None:
    start_script = REPO_ROOT / "scripts" / "start_app.py"

    assert start_script.exists()
    content = start_script.read_text(encoding="utf-8")

    assert 'DEFAULT_URL = "http://127.0.0.1:8000/phase2"' in content
    assert "webbrowser.open" in content
    assert "uvicorn.run" in content
