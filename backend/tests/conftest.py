import os
import tempfile

# Configure BEFORE importing the app: settings are cached at import time.
_tmp = tempfile.mkdtemp(prefix="anpr_test_")
os.environ["ANPR_DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'test.db')}"
os.environ["ANPR_EVIDENCE_DIR"] = os.path.join(_tmp, "evidence")
os.environ["ANPR_SECRET_KEY"] = "test-secret"
os.environ["ANPR_INGEST_API_KEY"] = "test-ingest-key"
os.environ["ANPR_FIRST_ADMIN_EMAIL"] = "admin@example.com"
os.environ["ANPR_FIRST_ADMIN_PASSWORD"] = "adminpass123"

import pytest
from fastapi.testclient import TestClient

from app.main import app

INGEST_KEY = "test-ingest-key"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:  # triggers lifespan: tables + admin
        yield test_client


@pytest.fixture(scope="session")
def admin_token(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "adminpass123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def viewer_headers(client, admin_headers):
    client.post(
        "/api/v1/users",
        json={"email": "viewer@example.com", "password": "viewerpass1", "role": "viewer"},
        headers=admin_headers,
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "viewer@example.com", "password": "viewerpass1"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
