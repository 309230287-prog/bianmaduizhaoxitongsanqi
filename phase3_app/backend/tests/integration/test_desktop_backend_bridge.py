from pathlib import Path


PHASE3_ROOT = Path(__file__).resolve().parents[3]


def test_desktop_shell_bootstraps_local_backend():
    main_rs = PHASE3_ROOT / "desktop" / "src-tauri" / "src" / "main.rs"

    assert main_rs.exists()
    content = main_rs.read_text(encoding="utf-8")

    assert "start_backend_if_needed" in content
    assert "product_code_mapper.api.app:create_app" in content
    assert "PYTHONPATH" in content
    assert "Command::new" in content
    assert "wait_for_backend" in content
