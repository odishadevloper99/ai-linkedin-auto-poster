import os

# Keep the test app intentionally unconfigured for Firebase. The route should
# fail closed (503) rather than pretending the database is healthy.
os.environ.pop("FIREBASE_DATABASE_URL", None)
os.environ.pop("FIREBASE_SERVICE_ACCOUNT_JSON", None)
os.environ["CRON_SECRET"] = "test"

from app.api import create_app


def test_health_route_exists_and_fails_closed_without_firebase():
    app = create_app()
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["database"] == "UNHEALTHY"


def test_cron_auth():
    app = create_app()
    client = app.test_client()
    assert client.post("/internal/cron/career").status_code == 401
