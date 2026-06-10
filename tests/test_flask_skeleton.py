"""Flask skeleton smoke tests."""

from app.app import create_app


def test_health_endpoint_returns_ok():
    """The skeleton exposes a health endpoint for smoke checks."""
    client = create_app().test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
