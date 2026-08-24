import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import runtime_credentials
from app.services.runtime_credentials import get_worker_credential_environment


@pytest.fixture
def client():
    original = os.environ.pop("MINERU_API_KEY", None)
    app = FastAPI()
    app.include_router(
        runtime_credentials.router,
        prefix="/api/v1/runtime-credentials",
    )
    try:
        yield TestClient(app)
    finally:
        os.environ.pop("MINERU_API_KEY", None)
        if original is not None:
            os.environ["MINERU_API_KEY"] = original


def test_mineru_credential_lifecycle_never_returns_secret(client: TestClient):
    status = client.get("/api/v1/runtime-credentials/mineru")
    assert status.status_code == 200
    assert status.json()["data"] == {
        "provider": "mineru",
        "configured": False,
        "persistence": "process_memory",
    }
    assert status.headers["cache-control"] == "no-store"

    secret = "test-only-mineru-secret"
    configured = client.put(
        "/api/v1/runtime-credentials/mineru",
        json={"api_key": secret},
    )
    assert configured.status_code == 200
    assert configured.json()["data"]["configured"] is True
    assert secret not in configured.text
    assert os.environ["MINERU_API_KEY"] == secret
    assert get_worker_credential_environment()["MINERU_API_KEY"] == secret
    assert configured.headers["cache-control"] == "no-store"

    refreshed = client.get("/api/v1/runtime-credentials/mineru")
    assert refreshed.json()["data"]["configured"] is True
    assert secret not in refreshed.text

    cleared = client.delete("/api/v1/runtime-credentials/mineru")
    assert cleared.status_code == 200
    assert cleared.json()["data"]["configured"] is False
    assert "MINERU_API_KEY" not in os.environ


def test_mineru_credential_rejects_blank_key(client: TestClient):
    response = client.put(
        "/api/v1/runtime-credentials/mineru",
        json={"api_key": "   "},
    )
    assert response.status_code == 422
    assert "MINERU_API_KEY" not in os.environ
