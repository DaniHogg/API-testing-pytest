import os
from dataclasses import dataclass
from typing import Any

import pytest
import requests


@dataclass(frozen=True)
class ApiConfig:
    """Runtime configuration for the API test suite, sourced from env vars."""

    base_url: str
    timeout_seconds: float


def _load_config() -> ApiConfig:
    return ApiConfig(
        base_url=os.getenv("BASE_URL", "https://qa-portfolio-api.onrender.com"),
        timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
    )


class ApiClient:
    """Thin wrapper around ``requests.Session`` with base_url + timeout baked in.

    Replaces the old module-level ``_get``/``_post`` helper functions in
    test_api.py with a single reusable, session-scoped fixture that also
    gives us connection pooling (via requests.Session) across the suite.
    """

    def __init__(self, config: ApiConfig, session: requests.Session):
        self._config = config
        self._session = session

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def _url(self, path: str) -> str:
        return f"{self._config.base_url}{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self._config.timeout_seconds)
        return self._session.request(method, self._url(path), **kwargs)

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("DELETE", path, **kwargs)


@pytest.fixture(scope="session")
def api_config() -> ApiConfig:
    return _load_config()


@pytest.fixture(scope="session")
def base_url(api_config: ApiConfig) -> str:
    """Base URL for all API tests.

    Defaults to the deployed Render backend. Override with BASE_URL env var
    to point at a local server or alternative environment. Kept as its own
    fixture (backed by api_config) since several tests just want the raw
    URL/string rather than a client.
    """
    return api_config.base_url


@pytest.fixture(scope="session")
def api_client(api_config: ApiConfig):
    """Session-scoped HTTP client for the API under test.

    Exposes .get/.post/.put/.patch/.delete convenience methods that already
    carry the configured base_url and request timeout, so individual tests
    don't need to repeat either.
    """
    with requests.Session() as session:
        yield ApiClient(api_config, session)
