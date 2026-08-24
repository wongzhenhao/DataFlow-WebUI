from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, SecretStr, field_validator

from app.api.v1.envelope import ApiResponse
from app.api.v1.resp import ok
from app.core.container import container
from app.services.runtime_credentials import (
    MINERU_KEY_ENV,
    clear_runtime_credential,
    clear_serving_credential,
    credential_is_configured,
    serving_credential_is_configured,
    set_runtime_credential,
    set_serving_credential,
)


router = APIRouter(tags=["runtime_credentials"])

class MinerUCredentialInput(BaseModel):
    api_key: SecretStr = Field(
        ...,
        repr=False,
        json_schema_extra={"writeOnly": True},
        description="MinerU API key. Accepted for this backend process only and never returned.",
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("API key must not be empty")
        return value


class ServingCredentialInput(BaseModel):
    api_key: SecretStr = Field(
        ...,
        repr=False,
        json_schema_extra={"writeOnly": True},
        description="Serving API key. Accepted for this backend process only and never returned.",
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("API key must not be empty")
        return value


class RuntimeCredentialStatus(BaseModel):
    provider: str
    configured: bool
    persistence: str = "process_memory"


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _status() -> RuntimeCredentialStatus:
    return RuntimeCredentialStatus(
        provider="mineru",
        configured=credential_is_configured(MINERU_KEY_ENV),
    )


@router.get(
    "/mineru",
    response_model=ApiResponse[RuntimeCredentialStatus],
    operation_id="get_mineru_runtime_credential_status",
    summary="Return whether the MinerU runtime credential is configured",
)
def get_mineru_runtime_credential_status(response: Response):
    _no_store(response)
    return ok(_status())


@router.put(
    "/mineru",
    response_model=ApiResponse[RuntimeCredentialStatus],
    operation_id="set_mineru_runtime_credential",
    summary="Set the MinerU credential for this backend process without persisting it",
)
def set_mineru_runtime_credential(payload: MinerUCredentialInput, response: Response):
    api_key = payload.api_key.get_secret_value().strip()
    set_runtime_credential(MINERU_KEY_ENV, api_key)
    _no_store(response)
    return ok(_status(), message="MinerU runtime credential configured")


@router.delete(
    "/mineru",
    response_model=ApiResponse[RuntimeCredentialStatus],
    operation_id="clear_mineru_runtime_credential",
    summary="Clear the MinerU credential from this backend process",
)
def clear_mineru_runtime_credential(response: Response):
    clear_runtime_credential(MINERU_KEY_ENV)
    _no_store(response)
    return ok(_status(), message="MinerU runtime credential cleared")


def _serving_status(serving_id: str) -> RuntimeCredentialStatus:
    if not container.serving_registry._get(serving_id):
        raise HTTPException(status_code=404, detail=f"Serving instance with id {serving_id} not found")
    return RuntimeCredentialStatus(
        provider=f"serving:{serving_id}",
        configured=serving_credential_is_configured(serving_id),
    )


@router.get(
    "/serving/{serving_id}",
    response_model=ApiResponse[RuntimeCredentialStatus],
    operation_id="get_serving_runtime_credential_status",
)
def get_serving_runtime_credential_status(serving_id: str, response: Response):
    _no_store(response)
    return ok(_serving_status(serving_id))


@router.put(
    "/serving/{serving_id}",
    response_model=ApiResponse[RuntimeCredentialStatus],
    operation_id="set_serving_runtime_credential",
)
def set_serving_runtime_credential(
    serving_id: str,
    payload: ServingCredentialInput,
    response: Response,
):
    _serving_status(serving_id)
    set_serving_credential(serving_id, payload.api_key.get_secret_value().strip())
    _no_store(response)
    return ok(_serving_status(serving_id), message="Serving runtime credential configured")


@router.delete(
    "/serving/{serving_id}",
    response_model=ApiResponse[RuntimeCredentialStatus],
    operation_id="clear_serving_runtime_credential",
)
def clear_serving_runtime_credential(serving_id: str, response: Response):
    _serving_status(serving_id)
    clear_serving_credential(serving_id)
    _no_store(response)
    return ok(_serving_status(serving_id), message="Serving runtime credential cleared")
