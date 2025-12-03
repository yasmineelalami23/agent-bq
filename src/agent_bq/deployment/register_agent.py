"""Agent registration module for Google Cloud Discovery Engine Agentspace.

This module handles the registration of deployed Agent Engine instances with
Discovery Engine Agentspace applications. Includes authentication, duplicate
detection, and RESTful API integration with the Discovery Engine API.
"""

import asyncio
import json
import os
from typing import Any
from urllib.parse import urlencode

import google.auth
import httpx
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import Request
from pydantic import BaseModel, Field

from .config import RegisterEnv, initialize_environment


class ProvisionedEngine(BaseModel):
    """Reasoning engine configuration."""

    engine: str = Field(alias="reasoningEngine")


class AdkAgentDefinition(BaseModel):
    """ADK agent definition structure."""

    provisioned_engine: ProvisionedEngine = Field(alias="provisionedReasoningEngine")


class Agent(BaseModel):
    """Agent registration data structure."""

    name: str
    display_name: str = Field(alias="displayName")
    adk_definition: AdkAgentDefinition | None = Field(
        default=None, alias="adkAgentDefinition"
    )

    @property
    def registration_id(self) -> str:
        """Extract the registration ID from the agent name."""
        return self.name.split("/")[-1]

    @property
    def agent_engine_id(self) -> str | None:
        """Extract the Agent Engine ID from the reasoning engine resource name."""
        if not self.adk_definition:
            return None

        try:
            reasoning_engine = self.adk_definition.provisioned_engine.engine
            return reasoning_engine.split("/")[-1]
        except (AttributeError, IndexError):
            return None


class AgentsResponse(BaseModel):
    """Response structure for agents list API."""

    agents: list[Agent] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)

    def print_raw_response(self) -> None:
        """Print the raw JSON response as a formatted string."""
        print(json.dumps(self.raw_response, indent=2))
        return


def test_environment() -> None:
    """Test function to validate the registration environment."""
    _ = initialize_environment(RegisterEnv)

    return


def setup_environment(env: RegisterEnv) -> dict[str, str]:
    """Set up the registration environment and return authenticated headers.

    Handles:
    - Google Cloud authentication with default credentials
    - Request headers preparation
    - API endpoint logging

    Args:
        env: RegisterEnv configuration instance.

    Returns:
        Dict containing authenticated request headers.

    Raises:
        DefaultCredentialsError: If Google Cloud authentication fails.
        SystemExit: If authentication fails.
    """
    # The GitHub Actions Workflow is configured to export an access token
    try:
        # access_token is type Any for compatibility with credentials.token
        access_token: Any = os.environ["GCP_ACCESS_TOKEN"]
    except KeyError:
        print("📭 GCP_ACCESS_TOKEN environment variable not set")
        print("🔐 Continuing to authenticate with ADC...")

        # Authenticate
        try:
            credentials: Credentials
            credentials, _ = google.auth.default()  # pyright: ignore[reportAssignmentType]
            credentials.refresh(Request())
            access_token = credentials.token
        except DefaultCredentialsError as e:
            print(f"❌ Error getting Application Default Credentials: {e}")
            print("💻 Try authenticating with 'gcloud auth application-default login'")
            exit(1)
        except RefreshError as e:
            print(f"❌ Error refreshing access token: {e}")
            exit(1)
        except Exception as e:
            print(f"❌ Unexpected error during authentication: {e}")
            exit(1)

    if not access_token:
        print(
            "❌ 🔑 No access token found: set the GCP_ACCESS_TOKEN environment variable"
            " or authenticate with ADC"
        )
        exit(1)

    # Prepare request headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": env.google_cloud_project,
    }

    return headers


async def get_agents_data(env: RegisterEnv, headers: dict[str, str]) -> AgentsResponse:
    """Return the agents registered with an Agentspace app.

    Args:
        env: RegisterEnv configuration instance.
        headers: Authenticated request headers.

    Returns:
        AgentsResponse: Parsed response containing the list of registered agents.

    Raises:
        SystemExit: If the request fails.

    """
    # Get the existing agent registrations
    print("🔍 Getting agent registrations...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(env.endpoint, headers=headers, timeout=30.0)
            response.raise_for_status()
            response_data = response.json()
            agents_data = AgentsResponse.model_validate(response_data)
            agents_data.raw_response = response_data
            print("✅ Got existing agent registrations!")
    except httpx.HTTPStatusError as err:
        print(f"❌ 🌐 HTTP error occurred: {err}")
        print(f"Response content: {err.response.text}")
        exit(1)
    except httpx.ConnectError as err:
        print(f"❌ 🔌 Connection error occurred: {err}")
        exit(1)
    except httpx.TimeoutException as err:
        print(f"❌ ⏱️ Timeout error occurred: {err}")
        exit(1)
    except httpx.RequestError as err:
        print(f"❌ ⚠️ An unexpected error occurred: {err}")
        exit(1)

    return agents_data


import os
from urllib.parse import urlencode
import httpx

# Ensure you have these imports available in your file
# from your_module import RegisterEnv (or wherever RegisterEnv is defined)

async def register_authorization(env: RegisterEnv, headers: dict[str, str]) -> None:
    """
    Registers OAuth using the 'Forced URL' strategy (Adapted from Jira example).
    Explicitly encodes response_type, scope, and access_type into the URL string.
    """
    print("🔐 Configuring OAuth Authorization (Jira Strategy)...")

    # 1. Retrieve Credentials
    try:
        client_id = os.environ["GOOGLE_CLIENT_ID"]
        client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
    except KeyError as e:
        print(f"❌ Missing required environment variable: {e}")
        return

    # 2. Define Scopes (Space-separated string, NOT a list)
    # We define them as a single string because we are encoding them manually.
    scopes_str = (
        "https://www.googleapis.com/auth/bigquery "
        "https://www.googleapis.com/auth/userinfo.email "
        "openid"
    )

    # 3. Build the Authorization URL Manually
    base_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    
    # We bake all parameters into the URL to ensure 'response_type' is present.
    # Google requires 'access_type=offline' to get a refresh token.
    params = {
        "access_type": "offline", 
        "prompt": "consent",
        "scope": scopes_str,
        "response_type": "code", # <--- Explicitly forcing the missing parameter
    }

    # Create the full URL: .../auth?access_type=offline&scope=...&response_type=code
    full_auth_uri = f"{base_auth_url}?{urlencode(params)}"

    # 4. Construct the Payload
    base_app_url = env.endpoint.rsplit("/", 1)[0]
    auth_id = "google-oauth"
    
    payload = {
        "name": f"{base_app_url.split('v1alpha/')[1]}/authorizations/{auth_id}",
        "serverSideOauth2": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "authorizationUri": full_auth_uri, # We pass the FULL URL here
            "tokenUri": "https://oauth2.googleapis.com/token",
            "pkceEnabled": True
        },
    }

    print(f"📦 Auth Payload Configured with URI: {full_auth_uri}")

    # 5. Send Request
    specific_auth_url = f"{base_app_url}/authorizations/{auth_id}?allowMissing=true"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                specific_auth_url, headers=headers, json=payload, timeout=30.0
            )
            response.raise_for_status()
            print("✅ Authorization configuration updated successfully!")
            
    except httpx.HTTPStatusError as err:
        print(f"❌ OAuth Configuration Failed: {err}")
        print(f"Response content: {err.response.text}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


async def register() -> None:
    """Register the agent with the Agentspace App.

    Handles the complete registration workflow including:
    - Environment variable validation
    - Google Cloud authentication with default credentials
    - Discovery Engine API endpoint construction
    - Duplicate registration detection
    - Agent registration via REST API

    Raises:
        KeyError: If required environment variables are missing.
        DefaultCredentialsError: If Google Cloud authentication fails.
        SystemExit: If environment validation or authentication fails.
    """
    # Load and validate environment configuration
    env = initialize_environment(RegisterEnv)

    headers: dict[str, str] = setup_environment(env)
    agents_data: AgentsResponse = await get_agents_data(env=env, headers=headers)

    # Check if the AGENT_ENGINE_ID is already registered
    existing_agent: Agent | None = next(
        (
            agent
            for agent in agents_data.agents
            if agent.agent_engine_id == env.agent_engine_id
        ),
        None,
    )

    if existing_agent:
        print(f"🤖 Agent {env.agent_engine_id} is already registered, skipping creation...")
    else:
        print(f"📭 Agent {env.agent_engine_id} not found, registering...")

        # Prepare the Agent definition JSON Payload
        payload = {
            "displayName": env.agent_display_name,
            "description": env.agent_description,
            "adk_agent_definition": {
                "tool_settings": {
                    "tool_description": env.agent_description,
                },
                "provisioned_reasoning_engine": {
                    "reasoning_engine": env.reasoning_engine,
                },
            },
        }

        print(f"📦 Payload:\n{json.dumps(payload, indent=2)}")

        # Register the Agent
        print(f"🔗 Registering Agent: {env.agent_display_name}...")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    env.endpoint, headers=headers, json=payload, timeout=30.0
                )
                response.raise_for_status()
                print("✅ Agent registered successfully!")
        except httpx.HTTPStatusError as err:
            print(f"❌ 🌐 HTTP error occurred: {err}")
            print(f"Response content: {err.response.text}")
            exit(1)
        except httpx.ConnectError as err:
            print(f"❌ 🔌 Connection error occurred: {err}")
            exit(1)
        except httpx.TimeoutException as err:
            print(f"❌ ⏱️ Timeout error occurred: {err}")
            exit(1)
        except httpx.RequestError as err:
            print(f"❌ ⚠️ An unexpected error occurred: {err}")
            exit(1)

    # --- NEW STEP: Register/Update Authorization ---
    # We call this regardless of whether the agent was just created or already existed,
    # to ensure the OAuth settings are always up to date.
    await register_authorization(env, headers)

    return


async def unregister() -> None:
    """Unregister the agent from the Agentspace App.

    Finds and removes the agent registration based on AGENT_ENGINE_ID.
    Prompts for user confirmation before proceeding to unregister.

    Raises:
        SystemExit: If user cancels the unregister operation or if it fails.
    """
    # Load and validate environment configuration
    env = initialize_environment(RegisterEnv, print_config=False)

    headers: dict[str, str] = setup_environment(env)
    agents_data: AgentsResponse = await get_agents_data(env=env, headers=headers)

    # Find the agent to unregister
    agent_to_unregister: Agent | None = next(
        (
            agent
            for agent in agents_data.agents
            if agent.agent_engine_id == env.agent_engine_id
        ),
        None,
    )

    # Exit if the AGENT_ENGINE_ID is not registered
    if not agent_to_unregister:
        print(
            f"❌ 📭 Agent Engine ID '{env.agent_engine_id}' is not currently"
            " registered with Agentspace"
        )
        return

    # Confirmation prompt
    response = input(
        f"🤔 Unregister Agent '{agent_to_unregister.display_name}' "
        f"with Agent Engine ID '{env.agent_engine_id}' "
        f"from Agentspace app '{env.agentspace_app_id}'? [y/N]: "
    )
    if response.lower() not in ["y", "yes"]:
        print("❌ Unregister operation cancelled")
        return

    # Construct DELETE endpoint for the specific agent
    delete_endpoint = f"{env.endpoint}/{agent_to_unregister.registration_id}"

    # Unregister the agent
    try:
        print(f"🔓 Unregistering agent {env.agent_engine_id}...")
        async with httpx.AsyncClient() as client:
            http_response = await client.delete(
                delete_endpoint, headers=headers, timeout=30.0
            )
            http_response.raise_for_status()
            print(
                f"✅ Agent {env.agent_engine_id} "
                "unregistered successfully from Agentspace"
            )
    except httpx.HTTPStatusError as err:
        print(f"❌ 🌐 HTTP error during unregister operation: {err}")
        print(f"Response content: {err.response.text}")
        exit(1)
    except httpx.RequestError as err:
        print(f"❌ ⚠️ Error during unregister operation: {err}")
        exit(1)

    return


async def list_agent_registrations() -> None:
    """List all agents registered with the Agentspace App."""
    # Load and validate environment configuration
    env = initialize_environment(RegisterEnv, print_config=False)

    headers: dict[str, str] = setup_environment(env)
    agents_data: AgentsResponse = await get_agents_data(env=env, headers=headers)

    if not agents_data.agents:
        print("📭 No agents currently registered with the Agentspace app.")
        return

    print("\n📡 Raw response:\n")
    agents_data.print_raw_response()
    print(f"\n🗂️ Agents registered with Agentspace app '{env.agentspace_app_id}':\n")
    for agent in agents_data.agents:
        print(f"- Display Name:    {agent.display_name}")
        print(f"  Registration ID: {agent.registration_id}")
        print(f"  Agent Engine ID: {agent.agent_engine_id}\n")

    return


# Sync wrapper functions for backwards compatibility and CLI usage
def main_register() -> None:
    """Synchronous wrapper for the async register function."""
    asyncio.run(register())


def main_unregister() -> None:
    """Synchronous wrapper for the async unregister function."""
    asyncio.run(unregister())


def main_list() -> None:
    """Synchronous wrapper for the async list_agent_registrations function."""
    asyncio.run(list_agent_registrations())