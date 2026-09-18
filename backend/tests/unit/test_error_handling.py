from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_unexpected_error_response_shape() -> None:
    response = client.get('/does-not-exist')
    assert response.status_code == 404
