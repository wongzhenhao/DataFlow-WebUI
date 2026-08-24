from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import runtime_credentials, serving
from app.core.container import container
from app.services.runtime_credentials import (
    clear_serving_credential,
    serving_credential_is_configured,
)
from app.services.serving_registry import ServingRegistry


@pytest.fixture
def serving_client(tmp_path: Path):
    original_registry = container.serving_registry
    registry_path = tmp_path / "serving_registry.yaml"
    container.serving_registry = ServingRegistry(path=str(registry_path))

    app = FastAPI()
    app.include_router(serving.router, prefix="/api/v1/serving")
    app.include_router(runtime_credentials.router, prefix="/api/v1/runtime-credentials")
    try:
        yield TestClient(app), registry_path
    finally:
        for serving_id in container.serving_registry._get_all():
            clear_serving_credential(serving_id)
        container.serving_registry = original_registry


def test_fresh_install_can_create_metadata_without_persisting_key(serving_client):
    client, registry_path = serving_client

    empty = client.get("/api/v1/serving/")
    assert empty.status_code == 200
    assert empty.json()["data"] == []

    secret = "test-only-serving-secret"
    created = client.post(
        "/api/v1/serving/",
        params={"name": "My scientific model", "cls_name": "APILLMServing_request"},
        json=[
            {"name": "api_url", "value": "https://example.invalid/v1/chat/completions"},
            {"name": "api_key", "value": secret},
            {"name": "model_name", "value": "science-model"},
            {"name": "max_workers", "value": 4},
        ],
    )
    assert created.status_code == 200
    serving_id = created.json()["data"]["id"]

    persisted = registry_path.read_text(encoding="utf-8")
    assert secret not in persisted
    assert "api_key" not in persisted
    assert "key_name_of_api_key" not in persisted

    listed = client.get("/api/v1/serving/").json()["data"]
    assert len(listed) == 1
    assert listed[0]["id"] == serving_id
    assert listed[0]["credential_configured"] is True
    assert all(param["name"] != "api_key" for param in listed[0]["params"])

    cleared = client.delete(f"/api/v1/runtime-credentials/serving/{serving_id}")
    assert cleared.json()["data"]["configured"] is False
    assert client.get("/api/v1/serving/").json()["data"][0]["credential_configured"] is False

    replacement = "test-only-replacement-secret"
    configured = client.put(
        f"/api/v1/runtime-credentials/serving/{serving_id}",
        json={"api_key": replacement},
    )
    assert configured.json()["data"]["configured"] is True
    assert replacement not in configured.text
    assert replacement not in registry_path.read_text(encoding="utf-8")


def test_legacy_yaml_secret_is_scrubbed_and_requires_reentry(tmp_path: Path):
    registry_path = tmp_path / "legacy_serving_registry.yaml"
    serving_id = "legacy-serving"
    secret = "test-only-legacy-secret"
    registry_path.write_text(
        yaml.safe_dump(
            {
                serving_id: {
                    "name": "legacy",
                    "cls_name": "APILLMServing_request",
                    "params": [
                        {"name": "api_url", "value": "https://example.invalid"},
                        {"name": "api_key", "value": secret},
                        {"name": "key_name_of_api_key", "value": "OLD_KEY_NAME"},
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    try:
        registry = ServingRegistry(path=str(registry_path))
        assert registry._get(serving_id) is not None
        assert serving_credential_is_configured(serving_id) is False
        scrubbed = registry_path.read_text(encoding="utf-8")
        assert secret not in scrubbed
        assert "api_key" not in scrubbed
        assert "key_name_of_api_key" not in scrubbed
        ServingRegistry(path=str(registry_path))
        assert serving_credential_is_configured(serving_id) is False
    finally:
        clear_serving_credential(serving_id)
