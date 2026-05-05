import os

import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for all API tests.

    Defaults to the deployed Render backend. Override with BASE_URL env var
    to point at a local server or alternative environment.
    """
    return os.getenv("BASE_URL", "https://qa-portfolio-api.onrender.com")
