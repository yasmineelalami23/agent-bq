"""Common fixtures for tests."""

from collections.abc import Callable, Generator
from contextlib import AbstractContextManager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def valid_base_env() -> dict[str, str]:
    """Valid environment variables for BaseEnv model.

    Returns:
        Dictionary with all required fields for BaseEnv.
    """
    return {
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "AGENT_NAME": "test-agent",
    }


@pytest.fixture
def valid_deploy_env() -> dict[str, str]:
    """Valid environment variables for DeployEnv model.

    Returns:
        Dictionary with all required fields for DeployEnv.
    """
    return {
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "AGENT_NAME": "test-agent",
        "GOOGLE_CLOUD_STORAGE_BUCKET": "test-bucket",
    }


@pytest.fixture
def valid_delete_env() -> dict[str, str]:
    """Valid environment variables for DeleteEnv model.

    Returns:
        Dictionary with all required fields for DeleteEnv.
    """
    return {
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "AGENT_NAME": "test-agent",
        "AGENT_ENGINE_ID": "test-engine-id",
    }


@pytest.fixture
def valid_register_env() -> dict[str, str]:
    """Valid environment variables for RegisterEnv model.

    Returns:
        Dictionary with all required fields for RegisterEnv.
    """
    return {
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "AGENT_NAME": "test-agent",
        "AGENT_ENGINE_ID": "test-engine-id",
        "AGENTSPACE_APP_ID": "test-app-id",
        "AGENTSPACE_APP_LOCATION": "us-central1",
    }


@pytest.fixture
def valid_remote_env() -> dict[str, str]:
    """Valid environment variables for RunRemoteEnv model.

    Returns:
        Dictionary with all required fields for RunRemoteEnv.
    """
    return {
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "AGENT_NAME": "test-agent",
        "AGENT_ENGINE_ID": "test-engine-id",
    }


@pytest.fixture
def valid_local_env() -> dict[str, str]:
    """Valid environment variables for RunLocalEnv model.

    Returns:
        Dictionary with minimal required fields for RunLocalEnv.
    """
    return {
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "AGENT_NAME": "test-agent",
    }


class MockEnviron(dict[str, str]):
    """Mock os.environ-like object for testing.

    Mimics os._Environ behavior while being a dict subclass.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize mock environ."""
        super().__init__(*args, **kwargs)


@pytest.fixture
def mock_environ() -> type[MockEnviron]:
    """Mock os.environ class for testing.

    Returns:
        MockEnviron class that behaves like os._Environ.
    """
    return MockEnviron


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clean environment variables before each test.

    Removes any existing environment variables that might interfere
    with tests to ensure isolation.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    env_vars_to_clean = [
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "AGENT_NAME",
        "GOOGLE_CLOUD_STORAGE_BUCKET",
        "GCS_DIR_NAME",
        "AGENT_DISPLAY_NAME",
        "AGENT_DESCRIPTION",
        "AGENT_ENGINE_ID",
        "LOG_LEVEL",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT",
        "AGENTSPACE_APP_ID",
        "AGENTSPACE_APP_LOCATION",
        "API_VERSION",
    ]

    for var in env_vars_to_clean:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_load_dotenv() -> Generator[MagicMock]:
    """Mock load_dotenv function for testing.

    Yields:
        Mock object for load_dotenv function.
    """
    with patch("agent_engine_cicd_base.deployment.config.load_dotenv") as mock:
        yield mock


@pytest.fixture
def mock_sys_exit() -> Generator[MagicMock]:
    """Mock sys.exit with SystemExit side effect for testing validation failures.

    Yields:
        Mock object for sys.exit that raises SystemExit(1).
    """
    with patch("sys.exit", side_effect=SystemExit(1)) as mock:
        yield mock


@pytest.fixture
def set_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[dict[str, str]], None]:
    """Helper fixture to set multiple environment variables at once.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        Function that takes a dictionary and sets all key-value pairs as env vars.
    """

    def _set_env(env_dict: dict[str, str]) -> None:
        """Set multiple environment variables from a dictionary.

        Args:
            env_dict: Dictionary of environment variable names and values.
        """
        for key, value in env_dict.items():
            monkeypatch.setenv(key, value)

    return _set_env


@pytest.fixture
def mock_print_config() -> Callable[[type], AbstractContextManager[MagicMock]]:
    """Context manager factory for mocking print_config on any model class.

    Returns:
        Function that returns a context manager for mocking print_config.
    """

    def _mock_config(model_class: type) -> AbstractContextManager[MagicMock]:
        """Create a context manager for mocking print_config on a model.

        Args:
            model_class: The Pydantic model class to mock print_config on.

        Returns:
            Context manager that yields the mock object.
        """
        return patch.object(model_class, "print_config")

    return _mock_config
