from typing import Any

from app.services.runtime_credentials import (
    serving_credential_env_name,
    serving_credential_is_configured,
)


SECRET_PARAM_NAMES = {"api_key", "key_name_of_api_key"}


class ServingCredentialMissingError(ValueError):
    pass


def parameter_value(param: dict[str, Any]) -> Any:
    value = param.get("value")
    return value if value is not None else param.get("default_value")


def extract_api_key(params: list[dict[str, Any]] | None) -> str | None:
    for param in params or []:
        if param.get("name") != "api_key":
            continue
        value = parameter_value(param)
        if value is None or "****" in str(value):
            return None
        value = str(value).strip()
        return value or None
    return None


def sanitize_serving_params(params: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [
        dict(param)
        for param in params or []
        if param.get("name") not in SECRET_PARAM_NAMES
    ]


def build_api_serving_init_params(
    serving_info: dict[str, Any],
    serving_id: str,
) -> dict[str, Any]:
    if not serving_credential_is_configured(serving_id):
        raise ServingCredentialMissingError(
            f"API credential is not configured for serving '{serving_id}' in this backend session"
        )

    params = {
        param["name"]: parameter_value(param)
        for param in sanitize_serving_params(serving_info.get("params"))
        if parameter_value(param) is not None
    }
    params["key_name_of_api_key"] = serving_credential_env_name(serving_id)
    return params
