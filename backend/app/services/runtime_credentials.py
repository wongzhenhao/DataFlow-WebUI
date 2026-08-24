import os
from threading import Lock


MINERU_KEY_ENV = "MINERU_API_KEY"
SERVING_KEY_ENV_PREFIX = "DF_API_KEY_"
_credential_lock = Lock()


def credential_is_configured(env_name: str) -> bool:
    with _credential_lock:
        return bool(os.environ.get(env_name))


def set_runtime_credential(env_name: str, value: str) -> None:
    with _credential_lock:
        os.environ[env_name] = value


def clear_runtime_credential(env_name: str) -> None:
    with _credential_lock:
        os.environ.pop(env_name, None)


def get_worker_credential_environment() -> dict[str, str]:
    """Return a copy of the allow-listed credentials for an isolated worker."""
    with _credential_lock:
        return {
            name: value
            for name, value in os.environ.items()
            if value and is_worker_credential_name(name)
        }


def serving_credential_env_name(serving_id: str) -> str:
    return f"{SERVING_KEY_ENV_PREFIX}{serving_id}"


def serving_credential_is_configured(serving_id: str) -> bool:
    return credential_is_configured(serving_credential_env_name(serving_id))


def set_serving_credential(serving_id: str, api_key: str) -> None:
    set_runtime_credential(serving_credential_env_name(serving_id), api_key)


def clear_serving_credential(serving_id: str) -> None:
    clear_runtime_credential(serving_credential_env_name(serving_id))


def is_worker_credential_name(name: str) -> bool:
    return name == MINERU_KEY_ENV or name.startswith(SERVING_KEY_ENV_PREFIX)


def clear_worker_credentials_from_environment() -> None:
    with _credential_lock:
        for name in list(os.environ):
            if is_worker_credential_name(name):
                os.environ.pop(name, None)
