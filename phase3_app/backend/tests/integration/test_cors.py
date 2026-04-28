from fastapi.testclient import TestClient

from product_code_mapper.api.app import create_app


def test_cors_allows_tauri_desktop_origin(tmp_path):
    client = TestClient(create_app(data_dir=tmp_path / "data"))

    response = client.options(
        "/settings/model",
        headers={
            "Origin": "http://tauri.localhost",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://tauri.localhost"
