from fastapi.testclient import TestClient

from product_code_mapper.api.app import create_app


def test_health_check():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

