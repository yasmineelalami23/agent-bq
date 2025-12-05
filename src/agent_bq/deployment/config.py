"""Environment configuration models for deployment operations.

This module provides Pydantic models for type-safe environment variable validation
and configuration management across different deployment operations. Each model
encapsulates the specific requirements for its corresponding operation, providing
clear contracts and better error messages.
"""

import json
import os
import sys
from collections.abc import Mapping
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    model_validator,
)


def initialize_environment[T: BaseModel](
    model_class: type[T],
    override_dotenv: bool = True,
    print_config: bool = True,
) -> T:
    """Initialize and validate environment configuration.

    Factory function that handles the common initialization pattern across all
    deployment scripts: load environment variables, validate with Pydantic model,
    handle errors, and optionally print configuration.

    Args:
        model_class: Pydantic model class to validate environment with.
        override_dotenv: Whether to override existing environment variables.
            Defaults to True for consistency and predictability.
        print_config: Whether to call print_config() method if it exists.
            Defaults to True.

    Returns:
        Validated environment configuration instance.

    Raises:
        SystemExit: If validation fails.

    Examples:
        >>> # Simple case (most common)
        >>> env = initialize_environment(DeployEnv)
        >>>
        >>> # Skip printing configuration
        >>> env = initialize_environment(RegisterEnv, print_config=False)
    """
    load_dotenv(override=override_dotenv)

    # Load and validate environment configuration
    try:
        env = model_class.model_validate(os.environ)
    except ValidationError as e:
        print("\n❌ Environment validation failed:\n")
        print(e)
        sys.exit(1)

    # Print configuration for user verification if method exists
    if print_config and hasattr(env, "print_config"):
        env.print_config()  # pyright: ignore[reportAttributeAccessIssue]

    return env


class ValidationBase(BaseModel):
    """Base model with empty string validation for all environment configurations.

    Provides common validation logic and configuration for handling environment
    variables across all deployment models. This ensures consistent behavior for
    both required and optional fields when dealing with empty strings from GitHub
    Actions.
    """

    @model_validator(mode="before")
    @classmethod
    def filter_empty_strings(cls, data: Any) -> Any:
        """Filter out empty strings before field validation.

        GitHub Actions return empty strings when repository variables don't exist,
        which breaks default value fallbacks. This validator removes empty strings
        from the input entirely, so Pydantic sees them as missing fields and uses
        defaults for optional fields.

        For required fields, the missing value will trigger a validation error.

        Ref: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables#using-the-vars-context-to-access-configuration-variable-values

        Args:
            data: Input data to validate (typically os.environ).

        Returns:
            Filtered data dict with empty strings removed.
        """
        if isinstance(data, Mapping):
            # Filter out empty string values so Pydantic uses defaults
            # Works with both dict and os._Environ
            return {k: v for k, v in data.items() if v != ""}
        return data

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both field names and aliases
        extra="ignore",  # Ignore extra env vars (system vars, etc.)
    )


class BaseEnv(ValidationBase):
    """Base environment configuration shared across deployment operations.

    Provides common fields required by most deployment operations.

    Attributes:
        google_cloud_project: GCP project ID.
        google_cloud_location: Vertex AI region (e.g., us-central1).
        agent_name: Unique agent identifier for resources and logs.
    """

    google_cloud_project: str = Field(
        ...,
        alias="GOOGLE_CLOUD_PROJECT",
        description="GCP project ID",
    )
    google_cloud_location: str = Field(
        ...,
        alias="GOOGLE_CLOUD_LOCATION",
        description="Vertex AI region (e.g., us-central1)",
    )
    agent_name: str = Field(
        ...,
        alias="AGENT_NAME",
        description="Unique agent identifier for resources and logs",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def service_account(self) -> str:
        """Agent Engine service account email (must exist with IAM roles)."""
        return (
            f"{self.agent_name}-app@{self.google_cloud_project}.iam.gserviceaccount.com"
        )


class DeployEnv(BaseEnv):
    """Environment configuration for deploy and update operations.

    Attributes:
        google_cloud_storage_bucket: GCS bucket for staging deployment artifacts.
        gcs_dir_name: Directory name within staging bucket.
        agent_display_name: Human-readable agent name.
        agent_description: Agent description for metadata.
        agent_engine_id: Existing engine ID for updates (None for new deployments).
        log_level: Logging verbosity level.
        otel_capture_content: OpenTelemetry message content capture setting.
    """

    google_cloud_storage_bucket: str = Field(
        ...,
        alias="GOOGLE_CLOUD_STORAGE_BUCKET",
        description="GCS bucket for staging deployment artifacts",
    )

    gcs_dir_name: str = Field(
        default="agent-engine-staging",
        alias="GCS_DIR_NAME",
        description="Directory name within staging bucket",
    )

    agent_display_name: str = Field(
        default="ADK Agent",
        alias="AGENT_DISPLAY_NAME",
        description="Human-readable agent name",
    )

    agent_description: str = Field(
        default="ADK Agent",
        alias="AGENT_DESCRIPTION",
        description="Agent description for metadata",
    )

    agent_engine_id: str | None = Field(
        default=None,
        alias="AGENT_ENGINE_ID",
        description="Existing engine ID for updates (None for new deployments)",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging verbosity level",
    )

    otel_capture_content: str = Field(
        default="true",
        alias="OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT",
        description="OpenTelemetry message content capture setting",
    )

    oauth_client_id: str | None = Field(
        default=None,
        alias="OAUTH_CLIENT_ID",
        description="OAuth client ID for BigQuery user authentication",
    )

    oauth_client_secret: str | None = Field(
        default=None,
        alias="OAUTH_CLIENT_SECRET",
        description="OAuth client secret for BigQuery user authentication",
    )

    gemini_enterprise_auth_id: str | None = Field(
        default=None,
        alias="GEMINI_ENTERPRISE_AUTH_ID",
        description="Auth ID key for Gemini Enterprise token in tool context state",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def agent_env_vars(self) -> dict[str, str]:
        """Runtime environment variables for Agent Engine AdkApp."""
        env_vars = {
            "AGENT_NAME": self.agent_name,
            "LOG_LEVEL": self.log_level,
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": (
                self.otel_capture_content
            ),
        }
        # Add OAuth credentials if configured
        if self.oauth_client_id:
            env_vars["OAUTH_CLIENT_ID"] = self.oauth_client_id
        if self.oauth_client_secret:
            env_vars["OAUTH_CLIENT_SECRET"] = self.oauth_client_secret
        if self.gemini_enterprise_auth_id:
            env_vars["GEMINI_ENTERPRISE_AUTH_ID"] = self.gemini_enterprise_auth_id
        return env_vars

    def print_config(self) -> None:
        """Print deployment configuration for user verification."""
        print("\n\n✅ Environment variables set for deployment:\n")
        print(f"GOOGLE_CLOUD_PROJECT:        {self.google_cloud_project}")
        print(f"GOOGLE_CLOUD_LOCATION:       {self.google_cloud_location}")
        print(f"GOOGLE_CLOUD_STORAGE_BUCKET: {self.google_cloud_storage_bucket}")
        print(f"AGENT_NAME:                  {self.agent_name}")
        print(f"GCS_DIR_NAME:                {self.gcs_dir_name}")
        print(f"AGENT_DISPLAY_NAME:          {self.agent_display_name}")
        print(f"AGENT_DESCRIPTION:           {self.agent_description}")
        print(f"AGENT_ENGINE_ID:             {self.agent_engine_id}")
        print(f"SERVICE_ACCOUNT:             {self.service_account}")
        oauth_id_display = "***" if self.oauth_client_id else None
        oauth_secret_display = "***" if self.oauth_client_secret else None
        print(f"OAUTH_CLIENT_ID:             {oauth_id_display}")
        print(f"OAUTH_CLIENT_SECRET:         {oauth_secret_display}")
        print(f"GEMINI_ENTERPRISE_AUTH_ID:   {self.gemini_enterprise_auth_id}")
        print("ENABLE_TRACING:              True")
        print("\n\n🤖 Environment variables set for Agent Engine AdkApp runtime:\n")
        # Mask secrets in output
        display_env_vars = self.agent_env_vars.copy()
        mask = "***"  # noqa: S105
        for key in ("OAUTH_CLIENT_ID", "OAUTH_CLIENT_SECRET"):
            if key in display_env_vars:
                display_env_vars[key] = mask
        print(f"{json.dumps(display_env_vars, indent=2)}\n\n")


class DeleteEnv(BaseEnv):
    """Environment configuration for delete operations.

    Attributes:
        agent_engine_id: Existing engine ID to delete (required).
    """

    agent_engine_id: str = Field(
        ...,
        alias="AGENT_ENGINE_ID",
        description="Existing engine ID to delete",
    )


class RegisterEnv(BaseEnv):
    """Environment configuration for Agentspace registration operations.

    Attributes:
        agent_engine_id: Agent Engine ID to register.
        agentspace_app_id: Agentspace application ID.
        agentspace_app_location: Agentspace application location.
        api_version: Discovery Engine API version.
        agent_display_name: Human-readable agent name.
        agent_description: Agent description for metadata.
    """

    agent_engine_id: str = Field(
        ...,
        alias="AGENT_ENGINE_ID",
        description="Agent Engine ID to register",
    )

    agentspace_app_id: str = Field(
        ...,
        alias="AGENTSPACE_APP_ID",
        description="Agentspace application ID",
    )

    agentspace_app_location: str = Field(
        ...,
        alias="AGENTSPACE_APP_LOCATION",
        description="Agentspace application location",
    )

    api_version: str = Field(
        default="v1alpha",
        alias="API_VERSION",
        description="Discovery Engine API version",
    )

    agent_display_name: str = Field(
        default="ADK Agent",
        alias="AGENT_DISPLAY_NAME",
        description="Human-readable agent name",
    )

    agent_description: str = Field(
        default="ADK Agent",
        alias="AGENT_DESCRIPTION",
        description="Agent description for metadata",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reasoning_engine(self) -> str:
        """Full resource name for the Agent Engine reasoning engine."""
        return (
            f"projects/{self.google_cloud_project}/"
            f"locations/{self.google_cloud_location}/"
            f"reasoningEngines/{self.agent_engine_id}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def endpoint(self) -> str:
        """Discovery Engine API endpoint for agent registration."""
        if self.agentspace_app_location == "global":
            server = "discoveryengine.googleapis.com"
        else:
            server = f"{self.agentspace_app_location}-discoveryengine.googleapis.com"

        return (
            f"https://{server}/{self.api_version}/projects/{self.google_cloud_project}/"
            f"locations/{self.agentspace_app_location}/collections/default_collection/"
            f"engines/{self.agentspace_app_id}/assistants/default_assistant/agents"
        )

    def print_config(self) -> None:
        """Print registration configuration for user verification."""
        print("\n\n✅ Environment variables set for registration:\n")
        print(f"GOOGLE_CLOUD_PROJECT:    {self.google_cloud_project}")
        print(f"GOOGLE_CLOUD_LOCATION:   {self.google_cloud_location}")
        print(f"API_VERSION:             {self.api_version}")
        print(f"AGENTSPACE_APP_ID:       {self.agentspace_app_id}")
        print(f"AGENTSPACE_APP_LOCATION: {self.agentspace_app_location}")
        print(f"AGENT_ENGINE_ID:         {self.agent_engine_id}")
        print(f"AGENT_DISPLAY_NAME:      {self.agent_display_name}")
        print(f"AGENT_DESCRIPTION:       {self.agent_description}")
        print(f"REASONING_ENGINE:        {self.reasoning_engine}")
        print(f"ENDPOINT:                {self.endpoint}\n\n")


class RunRemoteEnv(BaseEnv):
    """Environment configuration for remote agent testing.

    Attributes:
        agent_engine_id: Agent Engine ID to test.
    """

    agent_engine_id: str = Field(
        ...,
        alias="AGENT_ENGINE_ID",
        description="Agent Engine ID to test",
    )

    def print_config(self) -> None:
        """Print remote agent configuration for user verification."""
        print("\n\n✅ Environment variables set:\n")
        print(f"GOOGLE_CLOUD_PROJECT:  {self.google_cloud_project}")
        print(f"GOOGLE_CLOUD_LOCATION: {self.google_cloud_location}")
        print(f"AGENT_ENGINE_ID:       {self.agent_engine_id}\n\n")


class RunLocalEnv(ValidationBase):
    """Environment configuration for local agent development.

    Minimal configuration for local development server.

    Attributes:
        google_cloud_project: GCP project ID for trace export.
        agent_name: Unique agent identifier for resources and logs.
    """

    google_cloud_project: str = Field(
        ...,
        alias="GOOGLE_CLOUD_PROJECT",
        description="GCP project ID for trace export",
    )
    agent_name: str = Field(
        ...,
        alias="AGENT_NAME",
        description="Unique agent identifier for resources and logs",
    )

    def print_config(self) -> None:
        """Print local development configuration for user verification."""
        print("\n\n✅ Environment variables set:\n")
        print(f"GOOGLE_CLOUD_PROJECT: {self.google_cloud_project}")
        print(f"AGENT_NAME:           {self.agent_name}\n\n")


class TemplateConfig(BaseModel):
    """Configuration model for template initialization with validation.

    Used by init_template.py to validate repository names and derive package names.
    Enforces kebab-case repository naming for proper Python package compatibility.

    Attributes:
        repo_name: GitHub repository name in kebab-case format.
        package_name: Python package name (computed from repo_name).
    """

    repo_name: str = Field(
        ...,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
        description="GitHub repository name (kebab-case, e.g., 'my-agent')",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def package_name(self) -> str:
        """Python package name derived from repo_name (kebab-case → snake_case)."""
        return self.repo_name.replace("-", "_")
