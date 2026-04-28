from pathlib import Path

from fastapi.testclient import TestClient

from product_code_mapper.api.app import create_app


def test_health_check(tmp_path: Path):
    client = TestClient(create_app(data_dir=tmp_path / "data"))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_local_frontend_origin_is_allowed(tmp_path: Path):
    client = TestClient(create_app(data_dir=tmp_path / "data"))

    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_self_check_uses_configured_data_dir(tmp_path: Path, monkeypatch):
    configured_data_dir = tmp_path / "configured-data"
    unrelated_cwd = tmp_path / "cwd"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)
    client = TestClient(create_app(data_dir=configured_data_dir))

    response = client.get("/config/self-check")

    assert response.status_code == 200
    assert not (unrelated_cwd / "runtime_data").exists()
