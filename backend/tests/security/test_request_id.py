from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_request_id_header_is_present() -> None:
    response = client.get('/api/v1/health', headers={'x-request-id': 'req-123'})
    assert response.status_code == 200
    assert response.headers.get('x-request-id') == 'req-123'
