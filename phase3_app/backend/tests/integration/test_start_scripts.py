from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_start_workbench_script_documents_full_local_startup():
    script = PROJECT_ROOT / "scripts" / "start_workbench.ps1"

    assert script.exists()
    content = script.read_text(encoding="utf-8")
    assert "uvicorn product_code_mapper.api.app:create_app" in content
    assert "npm run dev" in content
    assert "http://127.0.0.1:5173" in content
    assert "-WindowStyle Hidden" in content
    assert "product-code-mapper.exe" in content
    assert "Invoke-RestMethod" in content


def test_chinese_double_click_launcher_uses_start_script():
    launcher = PROJECT_ROOT / "scripts" / "启动三期工作台.bat"

    assert launcher.exists()
    content = launcher.read_text(encoding="utf-8")
    assert "start_workbench.ps1" in content
    assert "ExecutionPolicy Bypass" in content
