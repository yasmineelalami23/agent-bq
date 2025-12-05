"""Gemini Enterprise credentials support for BigQuery toolsets.

This module provides custom credentials configuration and management classes
that support fetching OAuth tokens from Gemini Enterprise (Agentspace) via
the tool context state, while falling back to standard ADK OAuth flows for
local development.
"""

from collections.abc import Callable
from typing import Any, cast, override

import google.auth.credentials
import google.oauth2.credentials
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext
from google.adk.tools._google_credentials import (  # pyright: ignore[reportMissingImports]
    BaseGoogleCredentialsConfig,
    GoogleCredentialsManager,
)
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset, ToolPredicate
from google.adk.tools.bigquery import data_insights_tool, metadata_tool, query_tool
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.google_tool import (  # pyright: ignore[reportMissingImports]
    GoogleTool,
)
from pydantic import BaseModel, ConfigDict


class GeminiEnterpriseCredentialsConfig(BaseGoogleCredentialsConfig):
    """Credentials config with Gemini Enterprise auth ID support.

    This extends the base Google credentials config to support fetching
    OAuth tokens from Gemini Enterprise (Agentspace) via the tool context state.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    gemini_enterprise_auth_id: str | None = None
    """The auth ID key used by Gemini Enterprise to store the access token
    in the tool context state. When set, the credentials manager will first
    check for this token before falling back to the standard OAuth flow."""


class GeminiEnterpriseCredentialsManager(GoogleCredentialsManager):
    """Credentials manager for both local and Gemini Enterprise OAuth flows.

    This manager first checks for an access token provided by Gemini Enterprise
    (stored in the tool context state under the configured auth ID). If found,
    it creates credentials from that token. Otherwise, it falls back to the
    standard ADK OAuth flow for local development.
    """

    credentials_config: GeminiEnterpriseCredentialsConfig

    def __init__(self, credentials_config: GeminiEnterpriseCredentialsConfig):
        super().__init__(credentials_config)
        self.credentials_config = credentials_config

    async def get_valid_credentials(
        self, tool_context: ToolContext
    ) -> google.auth.credentials.Credentials | None:
        """Get valid credentials, checking Gemini Enterprise token first.

        Args:
            tool_context: The tool context containing state and auth methods

        Returns:
            Valid Credentials object, or None if OAuth flow is needed
        """
        auth_id = self.credentials_config.gemini_enterprise_auth_id

        # Check for Gemini Enterprise token first
        if auth_id:
            access_token = tool_context.state.get(auth_id)
            if access_token:
                return google.oauth2.credentials.Credentials(
                    token=access_token,
                    refresh_token=None,  # Gemini Enterprise handles refresh
                    token_uri="https://oauth2.googleapis.com/token",  # noqa: S106
                    client_id=self.credentials_config.client_id,
                    client_secret=self.credentials_config.client_secret,
                    scopes=(
                        list(self.credentials_config.scopes)
                        if self.credentials_config.scopes
                        else None
                    ),
                )

        # Fall back to standard ADK OAuth flow (for local development)
        return await super().get_valid_credentials(tool_context)


class GeminiEnterpriseGoogleTool(GoogleTool):
    """GoogleTool that uses GeminiEnterpriseCredentialsManager.

    This subclass overrides the credentials manager instantiation to use
    our custom manager that supports Gemini Enterprise tokens.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        *,
        credentials_config: GeminiEnterpriseCredentialsConfig | None = None,
        tool_settings: BaseModel | None = None,
    ):
        # Call FunctionTool.__init__ directly to avoid GoogleTool creating
        # the standard GoogleCredentialsManager
        FunctionTool.__init__(self, func=func)
        self._ignore_params.append("credentials")
        self._ignore_params.append("settings")
        self._credentials_manager = (
            GeminiEnterpriseCredentialsManager(credentials_config)
            if credentials_config
            else None
        )
        self._tool_settings = tool_settings


class GeminiEnterpriseBigQueryToolset(BaseToolset):
    """BigQuery Toolset that uses Gemini Enterprise credentials manager.

    This toolset creates tools that check for Gemini Enterprise OAuth tokens
    before falling back to the standard ADK OAuth flow.
    """

    def __init__(
        self,
        *,
        tool_filter: ToolPredicate | list[str] | None = None,
        credentials_config: GeminiEnterpriseCredentialsConfig | None = None,
        bigquery_tool_config: BigQueryToolConfig | None = None,
    ):
        super().__init__(tool_filter=tool_filter)
        self._credentials_config = credentials_config
        self._tool_settings = (
            bigquery_tool_config if bigquery_tool_config else BigQueryToolConfig()
        )

    def _is_tool_selected(
        self, tool: BaseTool, readonly_context: ReadonlyContext | None
    ) -> bool:
        """Check if a tool should be included based on the filter."""
        if self.tool_filter is None:
            return True

        if isinstance(self.tool_filter, list):
            return tool.name in self.tool_filter

        # tool_filter is a ToolPredicate
        if readonly_context is None:
            return True
        return self.tool_filter(tool, readonly_context)

    @override
    async def get_tools(
        self, readonly_context: ReadonlyContext | None = None
    ) -> list[BaseTool]:
        """Get tools from the toolset using Gemini Enterprise credentials."""
        tool_funcs: list[Callable[..., Any]] = [
            cast(Callable[..., Any], metadata_tool.get_dataset_info),
            cast(Callable[..., Any], metadata_tool.get_table_info),
            cast(Callable[..., Any], metadata_tool.list_dataset_ids),
            cast(Callable[..., Any], metadata_tool.list_table_ids),
            cast(Callable[..., Any], query_tool.get_execute_sql(self._tool_settings)),
            cast(Callable[..., Any], query_tool.forecast),
            cast(Callable[..., Any], query_tool.analyze_contribution),
            cast(Callable[..., Any], data_insights_tool.ask_data_insights),
        ]
        all_tools: list[BaseTool] = [
            GeminiEnterpriseGoogleTool(
                func=func,
                credentials_config=self._credentials_config,
                tool_settings=self._tool_settings,
            )
            for func in tool_funcs
        ]

        return [
            tool for tool in all_tools if self._is_tool_selected(tool, readonly_context)
        ]

    @override
    async def close(self) -> None:
        """Clean up resources."""
        pass
