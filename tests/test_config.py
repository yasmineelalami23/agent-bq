"""Comprehensive unit tests for scripts config module."""

import os
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from agent_engine_cicd_base.deployment.config import (
    BaseEnv,
    DeleteEnv,
    DeployEnv,
    RegisterEnv,
    RunLocalEnv,
    RunRemoteEnv,
    TemplateConfig,
    ValidationBase,
    initialize_environment,
)


class TestValidationBase:
    """Tests for ValidationBase model with empty string filtering."""

    def test_filter_empty_strings_with_dict(self) -> None:
        """Test that empty strings are filtered from dict input."""
        data = {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "GOOGLE_CLOUD_LOCATION": "",  # Empty string should be filtered
            "AGENT_NAME": "test-agent",
        }

        # Test with a simple ValidationBase subclass with aliases
        from pydantic import Field

        class TestModel(ValidationBase):
            google_cloud_project: str = Field(
                default="default-project", alias="GOOGLE_CLOUD_PROJECT"
            )
            google_cloud_location: str = Field(
                default="default-location", alias="GOOGLE_CLOUD_LOCATION"
            )
            agent_name: str = Field(default="default-agent", alias="AGENT_NAME")

        # The filter should remove empty string, using defaults
        model = TestModel.model_validate(data)
        assert model.google_cloud_project == "test-project"
        assert model.google_cloud_location == "default-location"  # Default used
        assert model.agent_name == "test-agent"

    def test_filter_empty_strings_with_os_environ(
        self, mock_environ: type[dict[str, str]]
    ) -> None:
        """Test that empty strings are filtered from os.environ-like input."""
        from pydantic import Field

        env = mock_environ(
            {
                "GOOGLE_CLOUD_PROJECT": "test-project",
                "GOOGLE_CLOUD_LOCATION": "",  # Empty string
                "AGENT_NAME": "test-agent",
            }
        )

        class TestModel(ValidationBase):
            google_cloud_project: str = Field(
                default="default-project", alias="GOOGLE_CLOUD_PROJECT"
            )
            google_cloud_location: str = Field(
                default="default-location", alias="GOOGLE_CLOUD_LOCATION"
            )
            agent_name: str = Field(default="default-agent", alias="AGENT_NAME")

        model = TestModel.model_validate(env)
        assert model.google_cloud_project == "test-project"
        assert model.google_cloud_location == "default-location"  # Default used
        assert model.agent_name == "test-agent"

    def test_filter_non_mapping_passthrough(self) -> None:
        """Test that non-mapping data passes through unchanged."""
        # This test verifies the validator doesn't break on non-Mapping input
        # In practice, Pydantic will convert non-Mapping data before validation
        # So the `return data` line for non-Mapping is defensive programming

        # Directly call the validator with non-Mapping data
        result = ValidationBase.filter_empty_strings("not a mapping")
        assert result == "not a mapping"

        result2 = ValidationBase.filter_empty_strings(123)
        assert result2 == 123

        result3 = ValidationBase.filter_empty_strings(None)
        assert result3 is None

    def test_empty_strings_cause_validation_error_for_required(self) -> None:
        """Test that empty strings cause validation errors for required."""
        data = {
            "GOOGLE_CLOUD_PROJECT": "",  # Empty string for required field
            "GOOGLE_CLOUD_LOCATION": "us-central1",
            "AGENT_NAME": "test-agent",
        }

        with pytest.raises(ValidationError) as exc_info:
            BaseEnv.model_validate(data)

        # Check that the error is about missing GOOGLE_CLOUD_PROJECT (alias)
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GOOGLE_CLOUD_PROJECT",) for error in errors), (
            "Should have error for GOOGLE_CLOUD_PROJECT"
        )

    def test_multiple_empty_strings_filtered(self) -> None:
        """Test that multiple empty strings are all filtered."""
        from pydantic import Field

        class TestModel(ValidationBase):
            google_cloud_project: str = Field(..., alias="GOOGLE_CLOUD_PROJECT")
            google_cloud_location: str | None = Field(
                default=None, alias="GOOGLE_CLOUD_LOCATION"
            )
            agent_name: str | None = Field(default=None, alias="AGENT_NAME")

        data = {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "GOOGLE_CLOUD_LOCATION": "",
            "AGENT_NAME": "",
            "EXTRA_FIELD": "",
        }

        # Empty strings should be filtered, only project remains
        model = TestModel.model_validate(data)
        assert model.google_cloud_project == "test-project"
        assert model.google_cloud_location is None  # Empty string filtered
        assert model.agent_name is None  # Empty string filtered

    def test_filter_keeps_nonempty_strings(self) -> None:
        """Test that the filter keeps non-empty strings and removes empty ones."""
        from pydantic import Field

        class TestModel(ValidationBase):
            field1: str | None = Field(default="default1", alias="FIELD1")
            field2: str | None = Field(default="default2", alias="FIELD2")
            field3: str | None = Field(default="default3", alias="FIELD3")
            field4: str | None = Field(default="default4", alias="FIELD4")

        # Mix of empty and non-empty values
        data = {
            "FIELD1": "value1",  # Non-empty - should be kept
            "FIELD2": "",  # Empty - should be filtered
            "FIELD3": "value3",  # Non-empty - should be kept
            "FIELD4": "",  # Empty - should be filtered
        }

        model = TestModel.model_validate(data)
        # Non-empty values should be preserved
        assert model.field1 == "value1"
        assert model.field3 == "value3"
        # Empty values should use defaults
        assert model.field2 == "default2"
        assert model.field4 == "default4"


class TestBaseEnv:
    """Tests for BaseEnv model."""

    def test_valid_base_env_creation(self, valid_base_env: dict[str, str]) -> None:
        """Test creating BaseEnv with valid required fields."""
        env = BaseEnv.model_validate(valid_base_env)

        assert env.google_cloud_project == "test-project"
        assert env.google_cloud_location == "us-central1"
        assert env.agent_name == "test-agent"

    def test_base_env_missing_required_field_raises_validation_error(self) -> None:
        """Test that missing required fields raise ValidationError."""
        data = {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            # Missing GOOGLE_CLOUD_LOCATION
            "AGENT_NAME": "test-agent",
        }

        with pytest.raises(ValidationError) as exc_info:
            BaseEnv.model_validate(data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GOOGLE_CLOUD_LOCATION",) for error in errors)

    def test_base_env_empty_string_required_field_raises_validation_error(
        self,
    ) -> None:
        """Test that empty strings for required fields raise errors."""
        data = {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "GOOGLE_CLOUD_LOCATION": "",  # Empty string
            "AGENT_NAME": "test-agent",
        }

        with pytest.raises(ValidationError) as exc_info:
            BaseEnv.model_validate(data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GOOGLE_CLOUD_LOCATION",) for error in errors)

    def test_service_account_computed_property(
        self, valid_base_env: dict[str, str]
    ) -> None:
        """Test that service_account property is computed correctly."""
        env = BaseEnv.model_validate(valid_base_env)

        expected = "test-agent-app@test-project.iam.gserviceaccount.com"
        assert env.service_account == expected

    def test_base_env_ignores_extra_fields(
        self, valid_base_env: dict[str, str]
    ) -> None:
        """Test that extra environment variables are ignored."""
        data = {**valid_base_env, "EXTRA_VAR": "extra-value", "PATH": "/usr/bin"}

        env = BaseEnv.model_validate(data)
        assert env.google_cloud_project == "test-project"
        # Extra fields should not be included
        assert not hasattr(env, "EXTRA_VAR")
        assert not hasattr(env, "PATH")


class TestDeployEnv:
    """Tests for DeployEnv model."""

    def test_valid_deploy_env_creation(self, valid_deploy_env: dict[str, str]) -> None:
        """Test creating DeployEnv with valid required fields."""
        env = DeployEnv.model_validate(valid_deploy_env)

        assert env.google_cloud_project == "test-project"
        assert env.google_cloud_location == "us-central1"
        assert env.agent_name == "test-agent"
        assert env.google_cloud_storage_bucket == "test-bucket"

    def test_deploy_env_optional_fields_use_defaults(
        self, valid_deploy_env: dict[str, str]
    ) -> None:
        """Test that optional fields use default values when not provided."""
        env = DeployEnv.model_validate(valid_deploy_env)

        # Check defaults
        assert env.gcs_dir_name == "agent-engine-staging"
        assert env.agent_display_name == "ADK Agent"
        assert env.agent_description == "ADK Agent"
        assert env.agent_engine_id is None
        assert env.log_level == "INFO"
        assert env.otel_capture_content == "true"

    def test_deploy_env_optional_fields_with_empty_strings_use_defaults(
        self, valid_deploy_env: dict[str, str]
    ) -> None:
        """Test that empty strings for optional fields result in defaults."""
        data = {
            **valid_deploy_env,
            "GCS_DIR_NAME": "",
            "AGENT_DISPLAY_NAME": "",
            "LOG_LEVEL": "",
            "AGENT_ENGINE_ID": "",
        }

        env = DeployEnv.model_validate(data)

        # Empty strings should be filtered, defaults used
        assert env.gcs_dir_name == "agent-engine-staging"
        assert env.agent_display_name == "ADK Agent"
        assert env.log_level == "INFO"
        assert env.agent_engine_id is None

    def test_deploy_env_optional_fields_with_values(
        self, valid_deploy_env: dict[str, str]
    ) -> None:
        """Test setting optional fields with actual values."""
        data = {
            **valid_deploy_env,
            "GCS_DIR_NAME": "custom-staging",
            "AGENT_DISPLAY_NAME": "Custom Agent",
            "AGENT_DESCRIPTION": "Custom Description",
            "AGENT_ENGINE_ID": "existing-engine-id",
            "LOG_LEVEL": "DEBUG",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false",
        }

        env = DeployEnv.model_validate(data)

        assert env.gcs_dir_name == "custom-staging"
        assert env.agent_display_name == "Custom Agent"
        assert env.agent_description == "Custom Description"
        assert env.agent_engine_id == "existing-engine-id"
        assert env.log_level == "DEBUG"
        assert env.otel_capture_content == "false"

    def test_agent_env_vars_computed_property(
        self, valid_deploy_env: dict[str, str]
    ) -> None:
        """Test that agent_env_vars property is computed correctly."""
        env = DeployEnv.model_validate(valid_deploy_env)

        expected = {
            "AGENT_NAME": "test-agent",
            "LOG_LEVEL": "INFO",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
        }
        assert env.agent_env_vars == expected

    def test_deploy_env_print_config(
        self, valid_deploy_env: dict[str, str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that print_config outputs expected information."""
        env = DeployEnv.model_validate(valid_deploy_env)
        env.print_config()

        captured = capsys.readouterr()
        output = captured.out

        # Check key information is printed
        assert "test-project" in output
        assert "us-central1" in output
        assert "test-bucket" in output
        assert "test-agent" in output
        assert "SERVICE_ACCOUNT" in output
        assert "test-agent-app@test-project.iam.gserviceaccount.com" in output
        assert "Agent Engine AdkApp runtime" in output

    def test_deploy_env_missing_required_storage_bucket(
        self, valid_base_env: dict[str, str]
    ) -> None:
        """Test that missing storage bucket raises ValidationError."""
        # valid_base_env doesn't include GOOGLE_CLOUD_STORAGE_BUCKET
        with pytest.raises(ValidationError) as exc_info:
            DeployEnv.model_validate(valid_base_env)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GOOGLE_CLOUD_STORAGE_BUCKET",) for error in errors)


class TestDeleteEnv:
    """Tests for DeleteEnv model."""

    def test_valid_delete_env_creation(self, valid_delete_env: dict[str, str]) -> None:
        """Test creating DeleteEnv with valid required fields."""
        env = DeleteEnv.model_validate(valid_delete_env)

        assert env.google_cloud_project == "test-project"
        assert env.google_cloud_location == "us-central1"
        assert env.agent_name == "test-agent"
        assert env.agent_engine_id == "test-engine-id"

    def test_delete_env_missing_agent_engine_id_raises_validation_error(
        self, valid_base_env: dict[str, str]
    ) -> None:
        """Test that missing agent_engine_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DeleteEnv.model_validate(valid_base_env)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("AGENT_ENGINE_ID",) for error in errors)

    def test_delete_env_empty_agent_engine_id_raises_validation_error(
        self, valid_base_env: dict[str, str]
    ) -> None:
        """Test that empty agent_engine_id raises ValidationError."""
        data = {**valid_base_env, "AGENT_ENGINE_ID": ""}

        with pytest.raises(ValidationError) as exc_info:
            DeleteEnv.model_validate(data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("AGENT_ENGINE_ID",) for error in errors)

    def test_delete_env_inherits_service_account(
        self, valid_delete_env: dict[str, str]
    ) -> None:
        """Test that DeleteEnv inherits service_account from BaseEnv."""
        env = DeleteEnv.model_validate(valid_delete_env)

        expected = "test-agent-app@test-project.iam.gserviceaccount.com"
        assert env.service_account == expected


class TestRegisterEnv:
    """Tests for RegisterEnv model."""

    def test_valid_register_env_creation(
        self, valid_register_env: dict[str, str]
    ) -> None:
        """Test creating RegisterEnv with valid required fields."""
        env = RegisterEnv.model_validate(valid_register_env)

        assert env.google_cloud_project == "test-project"
        assert env.google_cloud_location == "us-central1"
        assert env.agent_name == "test-agent"
        assert env.agent_engine_id == "test-engine-id"
        assert env.agentspace_app_id == "test-app-id"
        assert env.agentspace_app_location == "us-central1"

    def test_register_env_optional_fields_use_defaults(
        self, valid_register_env: dict[str, str]
    ) -> None:
        """Test that optional fields use default values."""
        env = RegisterEnv.model_validate(valid_register_env)

        assert env.api_version == "v1alpha"
        assert env.agent_display_name == "ADK Agent"
        assert env.agent_description == "ADK Agent"

    def test_register_env_optional_fields_with_values(
        self, valid_register_env: dict[str, str]
    ) -> None:
        """Test setting optional fields with actual values."""
        data = {
            **valid_register_env,
            "API_VERSION": "v1beta",
            "AGENT_DISPLAY_NAME": "Custom Agent",
            "AGENT_DESCRIPTION": "Custom Description",
        }

        env = RegisterEnv.model_validate(data)

        assert env.api_version == "v1beta"
        assert env.agent_display_name == "Custom Agent"
        assert env.agent_description == "Custom Description"

    def test_reasoning_engine_computed_property(
        self, valid_register_env: dict[str, str]
    ) -> None:
        """Test that reasoning_engine property is computed correctly."""
        env = RegisterEnv.model_validate(valid_register_env)

        expected = (
            "projects/test-project/locations/us-central1/"
            "reasoningEngines/test-engine-id"
        )
        assert env.reasoning_engine == expected

    def test_endpoint_computed_property_regional(
        self, valid_register_env: dict[str, str]
    ) -> None:
        """Test that endpoint property is computed correctly for regional location."""
        env = RegisterEnv.model_validate(valid_register_env)

        expected = (
            "https://us-central1-discoveryengine.googleapis.com/v1alpha/"
            "projects/test-project/locations/us-central1/collections/"
            "default_collection/engines/test-app-id/assistants/default_assistant/agents"
        )
        assert env.endpoint == expected

    def test_endpoint_computed_property_global(
        self, valid_register_env: dict[str, str]
    ) -> None:
        """Test that endpoint property is computed correctly for global location."""
        data = {**valid_register_env, "AGENTSPACE_APP_LOCATION": "global"}
        env = RegisterEnv.model_validate(data)

        expected = (
            "https://discoveryengine.googleapis.com/v1alpha/"
            "projects/test-project/locations/global/collections/"
            "default_collection/engines/test-app-id/assistants/default_assistant/agents"
        )
        assert env.endpoint == expected

    def test_register_env_print_config(
        self, valid_register_env: dict[str, str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that print_config outputs expected information."""
        env = RegisterEnv.model_validate(valid_register_env)
        env.print_config()

        captured = capsys.readouterr()
        output = captured.out

        # Check key information is printed
        assert "test-project" in output
        assert "us-central1" in output
        assert "test-app-id" in output
        assert "test-engine-id" in output
        assert "REASONING_ENGINE" in output
        assert "ENDPOINT" in output
        assert "reasoningEngines/test-engine-id" in output

    def test_register_env_missing_required_fields(
        self, valid_base_env: dict[str, str]
    ) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterEnv.model_validate(valid_base_env)

        errors = exc_info.value.errors()
        # Should have errors for required fields: engine_id, app_id, app_location
        assert any(error["loc"] == ("AGENT_ENGINE_ID",) for error in errors)
        assert any(error["loc"] == ("AGENTSPACE_APP_ID",) for error in errors)
        assert any(error["loc"] == ("AGENTSPACE_APP_LOCATION",) for error in errors)


class TestRunRemoteEnv:
    """Tests for RunRemoteEnv model."""

    def test_valid_remote_env_creation(self, valid_remote_env: dict[str, str]) -> None:
        """Test creating RunRemoteEnv with valid required fields."""
        env = RunRemoteEnv.model_validate(valid_remote_env)

        assert env.google_cloud_project == "test-project"
        assert env.google_cloud_location == "us-central1"
        assert env.agent_name == "test-agent"
        assert env.agent_engine_id == "test-engine-id"

    def test_remote_env_missing_agent_engine_id(
        self, valid_base_env: dict[str, str]
    ) -> None:
        """Test that missing agent_engine_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RunRemoteEnv.model_validate(valid_base_env)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("AGENT_ENGINE_ID",) for error in errors)

    def test_remote_env_print_config(
        self, valid_remote_env: dict[str, str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that print_config outputs expected information."""
        env = RunRemoteEnv.model_validate(valid_remote_env)
        env.print_config()

        captured = capsys.readouterr()
        output = captured.out

        assert "test-project" in output
        assert "us-central1" in output
        assert "test-engine-id" in output

    def test_remote_env_inherits_service_account(
        self, valid_remote_env: dict[str, str]
    ) -> None:
        """Test that RunRemoteEnv inherits service_account from BaseEnv."""
        env = RunRemoteEnv.model_validate(valid_remote_env)

        expected = "test-agent-app@test-project.iam.gserviceaccount.com"
        assert env.service_account == expected


class TestRunLocalEnv:
    """Tests for RunLocalEnv model."""

    def test_valid_local_env_creation(self, valid_local_env: dict[str, str]) -> None:
        """Test creating RunLocalEnv with minimal required fields."""
        env = RunLocalEnv.model_validate(valid_local_env)

        assert env.google_cloud_project == "test-project"
        assert env.agent_name == "test-agent"

    def test_local_env_missing_project_raises_validation_error(self) -> None:
        """Test that missing google_cloud_project raises ValidationError."""
        data: dict[str, str] = {}

        with pytest.raises(ValidationError) as exc_info:
            RunLocalEnv.model_validate(data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GOOGLE_CLOUD_PROJECT",) for error in errors)

    def test_local_env_empty_project_raises_validation_error(self) -> None:
        """Test that empty google_cloud_project raises ValidationError."""
        data = {"GOOGLE_CLOUD_PROJECT": ""}

        with pytest.raises(ValidationError) as exc_info:
            RunLocalEnv.model_validate(data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GOOGLE_CLOUD_PROJECT",) for error in errors)

    def test_local_env_missing_agent_name_raises_validation_error(self) -> None:
        """Test that missing agent_name raises ValidationError."""
        data = {"GOOGLE_CLOUD_PROJECT": "test-project"}

        with pytest.raises(ValidationError) as exc_info:
            RunLocalEnv.model_validate(data)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("AGENT_NAME",) for error in errors)

    def test_local_env_print_config(
        self, valid_local_env: dict[str, str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that print_config outputs expected information."""
        env = RunLocalEnv.model_validate(valid_local_env)
        env.print_config()

        captured = capsys.readouterr()
        output = captured.out

        assert "test-project" in output
        assert "GOOGLE_CLOUD_PROJECT" in output
        assert "test-agent" in output
        assert "AGENT_NAME" in output

    def test_local_env_ignores_extra_fields(
        self, valid_local_env: dict[str, str]
    ) -> None:
        """Test that extra fields are ignored."""
        data = {
            **valid_local_env,
            "GOOGLE_CLOUD_LOCATION": "ignored",
            "EXTRA_FIELD": "ignored",
        }

        env = RunLocalEnv.model_validate(data)
        assert env.google_cloud_project == "test-project"
        assert env.agent_name == "test-agent"
        assert not hasattr(env, "google_cloud_location")
        assert not hasattr(env, "extra_field")


class TestInitializeEnvironment:
    """Tests for initialize_environment factory function."""

    def test_initialize_environment_success(
        self,
        valid_deploy_env: dict[str, str],
        set_environment: Any,
        mock_load_dotenv: MagicMock,
    ) -> None:
        """Test successful environment initialization."""
        # Set environment variables
        set_environment(valid_deploy_env)

        env = initialize_environment(DeployEnv, print_config=False)

        mock_load_dotenv.assert_called_once_with(override=True)
        assert env.google_cloud_project == "test-project"
        assert env.agent_name == "test-agent"

    def test_initialize_environment_validation_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mock_load_dotenv: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test that validation failure causes sys.exit."""
        # Set incomplete environment (missing required field)
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        # Missing GOOGLE_CLOUD_LOCATION and AGENT_NAME

        with pytest.raises(SystemExit):
            initialize_environment(BaseEnv, print_config=False)

        mock_sys_exit.assert_called_once_with(1)

    def test_initialize_environment_prints_config_by_default(
        self,
        valid_deploy_env: dict[str, str],
        set_environment: Any,
        mock_load_dotenv: MagicMock,
        mock_print_config: Any,
    ) -> None:
        """Test that print_config is called by default."""
        set_environment(valid_deploy_env)

        with mock_print_config(DeployEnv) as mock_print:
            initialize_environment(DeployEnv)

        mock_print.assert_called_once()

    def test_initialize_environment_skip_print_config(
        self,
        valid_deploy_env: dict[str, str],
        set_environment: Any,
        mock_load_dotenv: MagicMock,
        mock_print_config: Any,
    ) -> None:
        """Test that print_config can be skipped."""
        set_environment(valid_deploy_env)

        with mock_print_config(DeployEnv) as mock_print:
            initialize_environment(DeployEnv, print_config=False)

        mock_print.assert_not_called()

    def test_initialize_environment_override_dotenv_false(
        self,
        valid_deploy_env: dict[str, str],
        set_environment: Any,
        mock_load_dotenv: MagicMock,
    ) -> None:
        """Test that override_dotenv can be set to False."""
        set_environment(valid_deploy_env)

        initialize_environment(DeployEnv, override_dotenv=False, print_config=False)

        mock_load_dotenv.assert_called_once_with(override=False)

    def test_initialize_environment_prints_validation_errors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        mock_load_dotenv: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test that validation errors are printed before exit."""
        # Set incomplete environment
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

        with pytest.raises(SystemExit):
            initialize_environment(BaseEnv, print_config=False)

        captured = capsys.readouterr()
        assert "Environment validation failed" in captured.out

    def test_initialize_environment_with_model_without_print_config(
        self,
        valid_local_env: dict[str, str],
        set_environment: Any,
        mock_load_dotenv: MagicMock,
    ) -> None:
        """Test initialization with a model that has print_config method."""
        from pydantic import Field

        set_environment(valid_local_env)

        # Create a test model without print_config
        class TestModelNoConfig(ValidationBase):
            google_cloud_project: str = Field(..., alias="GOOGLE_CLOUD_PROJECT")

        # Should not raise even though model doesn't have print_config
        env = initialize_environment(TestModelNoConfig, print_config=True)
        assert env.google_cloud_project == "test-project"


class TestEdgeCases:
    """Tests for edge cases and GitHub Actions scenarios."""

    def test_github_actions_empty_strings_scenario(
        self, valid_deploy_env: dict[str, str]
    ) -> None:
        """Test GitHub Actions scenario where unset variables return empty strings."""
        # Simulate GitHub Actions behavior: unset optional vars return empty strings
        data = {
            **valid_deploy_env,
            "AGENT_ENGINE_ID": "",  # GitHub Actions returns empty string
            "LOG_LEVEL": "",  # GitHub Actions returns empty string
            "AGENT_DISPLAY_NAME": "",  # GitHub Actions returns empty string
        }

        env = DeployEnv.model_validate(data)

        # Should use defaults for empty string optional fields
        assert env.agent_engine_id is None
        assert env.log_level == "INFO"
        assert env.agent_display_name == "ADK Agent"

    def test_all_empty_strings_raises_validation_error(self) -> None:
        """Test that all empty strings cause validation error for required fields."""
        data = {
            "GOOGLE_CLOUD_PROJECT": "",
            "GOOGLE_CLOUD_LOCATION": "",
            "AGENT_NAME": "",
        }

        with pytest.raises(ValidationError) as exc_info:
            BaseEnv.model_validate(data)

        # Should have errors for all required fields
        errors = exc_info.value.errors()
        assert len(errors) >= 3

    def test_mixed_valid_and_empty_values(self) -> None:
        """Test mixed valid values and empty strings."""
        data = {
            "GOOGLE_CLOUD_PROJECT": "valid-project",
            "GOOGLE_CLOUD_LOCATION": "",  # Empty
            "AGENT_NAME": "valid-agent",
            "GOOGLE_CLOUD_STORAGE_BUCKET": "",  # Empty
            "LOG_LEVEL": "",  # Empty optional
        }

        with pytest.raises(ValidationError) as exc_info:
            DeployEnv.model_validate(data)

        # Should have errors for required empty fields
        errors = exc_info.value.errors()
        error_fields = [error["loc"][0] for error in errors]
        assert "GOOGLE_CLOUD_LOCATION" in error_fields
        assert "GOOGLE_CLOUD_STORAGE_BUCKET" in error_fields
        # LOG_LEVEL should not cause error (optional with default)

    def test_actual_os_environ_compatibility(
        self, valid_base_env: dict[str, str], set_environment: Any
    ) -> None:
        """Test that models work with actual os.environ."""
        set_environment(valid_base_env)

        # Test with actual os.environ (not a mock)
        env = BaseEnv.model_validate(os.environ)
        assert env.google_cloud_project == "test-project"
        assert env.google_cloud_location == "us-central1"
        assert env.agent_name == "test-agent"

    def test_case_sensitivity_of_env_vars(self) -> None:
        """Test that env var names are case-sensitive but Pydantic handles both."""
        # Pydantic handles both field names and aliases
        data = {
            "google_cloud_project": "test-project",  # lowercase field name
            "GOOGLE_CLOUD_LOCATION": "us-central1",  # uppercase alias
            "AGENT_NAME": "test-agent",
        }

        # Succeeds: populate_by_name=True allows both field names and aliases
        env = BaseEnv.model_validate(data)
        assert env.google_cloud_project == "test-project"

    def test_unicode_values_in_env_vars(self, valid_deploy_env: dict[str, str]) -> None:
        """Test that unicode values are handled correctly."""
        data = {
            **valid_deploy_env,
            "AGENT_DISPLAY_NAME": "テストエージェント",  # Japanese
            "AGENT_DESCRIPTION": "描述 with 中文",  # Mixed languages
        }

        env = DeployEnv.model_validate(data)
        assert env.agent_display_name == "テストエージェント"
        assert env.agent_description == "描述 with 中文"

    def test_very_long_values(self, valid_deploy_env: dict[str, str]) -> None:
        """Test handling of very long values."""
        long_string = "a" * 10000
        data = {
            **valid_deploy_env,
            "AGENT_DESCRIPTION": long_string,
        }

        env = DeployEnv.model_validate(data)
        assert env.agent_description == long_string
        assert len(env.agent_description) == 10000


class TestTemplateConfig:
    """Test suite for TemplateConfig model used in template initialization."""

    def test_valid_repo_names(self) -> None:
        """Test that valid kebab-case repo names are accepted."""
        valid_names = [
            ("my-agent", "my_agent"),
            ("agent-engine-cicd-base", "agent_engine_cicd_base"),
            ("a", "a"),
            ("agent-v2", "agent_v2"),
            ("cool-app-123", "cool_app_123"),
            ("x9-test-456", "x9_test_456"),
            ("my-cool-agent", "my_cool_agent"),
        ]

        for repo_name, expected_package in valid_names:
            config = TemplateConfig(repo_name=repo_name)
            assert config.repo_name == repo_name
            assert config.package_name == expected_package

    def test_invalid_repo_names_uppercase(self) -> None:
        """Test that repo names with uppercase are rejected."""
        invalid_names = [
            "MyNewRepo",
            "My-Agent",
            "MY-AGENT",
            "My-Cool-Agent",
            "AgentV2",
        ]

        for invalid_name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                TemplateConfig(repo_name=invalid_name)

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["loc"] == ("repo_name",)
            assert "string_pattern_mismatch" in errors[0]["type"]

    def test_invalid_repo_names_underscore(self) -> None:
        """Test that repo names with underscores are rejected."""
        invalid_names = [
            "my_agent",
            "my_cool_agent",
            "agent_v2",
            "my-agent_test",
        ]

        for invalid_name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                TemplateConfig(repo_name=invalid_name)

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["loc"] == ("repo_name",)

    def test_invalid_repo_names_hyphens_at_boundaries(self) -> None:
        """Test that repo names starting or ending with hyphen are rejected."""
        invalid_names = [
            "-my-agent",
            "my-agent-",
            "-agent-",
            "-",
        ]

        for invalid_name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                TemplateConfig(repo_name=invalid_name)

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["loc"] == ("repo_name",)

    def test_invalid_repo_names_special_characters(self) -> None:
        """Test that repo names with special characters are rejected."""
        invalid_names = [
            "my.agent",
            "my@agent",
            "my agent",  # space
            "my_agent!",
            "my-agent#test",
        ]

        for invalid_name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                TemplateConfig(repo_name=invalid_name)

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["loc"] == ("repo_name",)

    def test_empty_repo_name(self) -> None:
        """Test that empty repo name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateConfig(repo_name="")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("repo_name",)

    def test_package_name_derivation(self) -> None:
        """Test that package_name is correctly derived from repo_name."""
        test_cases = [
            ("my-agent", "my_agent"),
            ("single", "single"),
            ("multi-word-name", "multi_word_name"),
            ("with-numbers-123", "with_numbers_123"),
            ("a1-b2-c3", "a1_b2_c3"),
        ]

        for repo_name, expected_package in test_cases:
            config = TemplateConfig(repo_name=repo_name)
            assert config.package_name == expected_package

    def test_package_name_is_computed_field(self) -> None:
        """Test that package_name is a computed field, not settable."""
        config = TemplateConfig(repo_name="my-agent")

        # Verify package_name exists
        assert config.package_name == "my_agent"

        # Attempting to set package_name should fail (computed fields are read-only)
        with pytest.raises((AttributeError, ValidationError)):
            config.package_name = "different_name"  # type: ignore[misc]

    def test_model_dict_includes_computed_field(self) -> None:
        """Test that model_dump includes the computed package_name field."""
        config = TemplateConfig(repo_name="my-agent")
        data = config.model_dump()

        assert "repo_name" in data
        assert "package_name" in data
        assert data["repo_name"] == "my-agent"
        assert data["package_name"] == "my_agent"

    def test_single_character_repo_name(self) -> None:
        """Test that single character repo names are valid."""
        valid_single_chars = ["a", "b", "z", "0", "9"]

        for char in valid_single_chars:
            config = TemplateConfig(repo_name=char)
            assert config.repo_name == char
            assert config.package_name == char

    def test_repo_name_with_consecutive_hyphens(self) -> None:
        """Test that consecutive hyphens in middle of name are valid."""
        # Pattern allows consecutive hyphens in the middle
        config = TemplateConfig(repo_name="my--agent")
        assert config.repo_name == "my--agent"
        assert config.package_name == "my__agent"
