from pathlib import Path

from fastapi.testclient import TestClient

from product_code_mapper.api.app import create_app


def test_model_settings_can_be_saved_without_echoing_api_key(tmp_path: Path):
    client = TestClient(create_app(data_dir=tmp_path / "data"))

    response = client.put(
        "/settings/model",
        json={
            "provider": "DeepSeek",
            "model_name": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "api_key": "sk-test-secret",
        },
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "DeepSeek"
    assert response.json()["model_name"] == "deepseek-chat"
    assert response.json()["has_api_key"] is True
    assert "api_key" not in response.json()
    assert "sk-test-secret" not in response.text


def test_blank_api_key_update_preserves_existing_secret(tmp_path: Path):
    client = TestClient(create_app(data_dir=tmp_path / "data"))

    first = client.put(
        "/settings/model",
        json={
            "provider": "DeepSeek",
            "model_name": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "api_key": "sk-test-secret",
        },
    )
    assert first.status_code == 200

    second = client.put(
        "/settings/model",
        json={
            "provider": "DeepSeek",
            "model_name": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "api_key": "",
            "data_dir": "D:\\data",
        },
    )

    assert second.status_code == 200
    assert second.json()["has_api_key"] is True


def test_model_settings_test_reports_missing_key_in_chinese(tmp_path: Path):
    client = TestClient(create_app(data_dir=tmp_path / "data"))

    response = client.post("/settings/model/test")

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "API Key" in response.json()["message"]
