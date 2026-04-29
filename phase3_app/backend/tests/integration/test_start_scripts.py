from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_start_workbench_script_launches_desktop_client_only():
    script = PROJECT_ROOT / "scripts" / "start_workbench.ps1"

    assert script.exists()
    content = script.read_text(encoding="utf-8")
    assert "product-code-mapper.exe" in content
    assert "Start-Process -FilePath $desktopExe" in content
    assert "Start-Process $workbenchUrl" not in content
    assert "npm run dev" not in content
    assert "python -m uvicorn" not in content


def test_start_workbench_prefers_desktop_owned_backend():
    script = PROJECT_ROOT / "scripts" / "start_workbench.ps1"

    content = script.read_text(encoding="utf-8")
    assert "桌面程序会自动连接本地后端" in content
    assert "uvicorn product_code_mapper.api.app:create_app" not in content


def test_chinese_double_click_launcher_uses_start_script():
    launcher = PROJECT_ROOT / "scripts" / "启动三期工作台.bat"

    assert launcher.exists()
    content = launcher.read_text(encoding="utf-8")
    assert "start_workbench.ps1" in content
    assert "ExecutionPolicy Bypass" in content


def test_dev_debug_script_keeps_web_debug_workflow():
    script = PROJECT_ROOT / "scripts" / "start_dev_debug.ps1"

    assert script.exists()
    content = script.read_text(encoding="utf-8")
    assert "python -m uvicorn product_code_mapper.api.app:create_app" in content
    assert "npm run dev" in content
    assert "http://127.0.0.1:5173" in content
    assert "Start-Process $workbenchUrl" in content
    assert "Invoke-RestMethod" in content


def test_chinese_dev_debug_launcher_uses_debug_script():
    launcher = PROJECT_ROOT / "scripts" / "开发调试启动.bat"

    assert launcher.exists()
    content = launcher.read_text(encoding="utf-8")
    assert "start_dev_debug.ps1" in content
    assert "ExecutionPolicy Bypass" in content
