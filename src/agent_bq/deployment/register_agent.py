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




# Ensure you have these imports available in your file
# from your_module import RegisterEnv (or wherever RegisterEnv is defined)

import os
import json
import httpx
from urllib.parse import urlencode

# Ensure you have 'PROJECT', 'AGENTSPACE_APP_LOCATION', 'API_VERSION' defined 
# or imported from your config/environment setup in this file.

async def register_authorization(env: RegisterEnv, headers: dict[str, str]) -> None:
    """Create or Overwrite a Google Authorization resource for BigQuery.
    
    Adapted from the Jira/Confluence strategy:
    1. Checks Env Vars
    2. Deletes existing auth if present (to avoid 409 conflict/update issues)
    3. Creates a fresh one with 'POST'
    """
    
    # 1. Check for required environment variables
    # We use the standard Google Auth variables
    auth_id = "google-oauth"
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Validation
    if not all([client_id, client_secret]):
        print("❌ Missing required environment variables:")
        if not client_id: print("   - GOOGLE_CLIENT_ID")
        if not client_secret: print("   - GOOGLE_CLIENT_SECRET")
        return

    # 2. Setup Endpoints (Project/Location level)
    # Note: Authorizations live at Project/Location, NOT inside the Engine/Agent.
    location_prefix = "" if env.location == "global" else f"{env.location}-"
    
    # Base URL for Authorizations
    base_url = (
        f"https://{location_prefix}discoveryengine.googleapis.com/v1alpha/"
        f"projects/{env.project_id}/locations/{env.location}/authorizations"
    )
    
    # Specific Resource URL (for deletion)
    resource_url = f"{base_url}/{auth_id}"
    
    # Creation URL (for POST)
    create_url = f"{base_url}?authorizationId={auth_id}"

    # 3. Prepare the Manual URL (The "Jira Strategy")
    # We manually build the URL to ensure 'response_type=code' is present.
    scopes = "https://www.googleapis.com/auth/bigquery https://www.googleapis.com/auth/userinfo.email openid"
    
    params = {
        "access_type": "offline", # Required for refresh tokens
        "prompt": "consent",
        "scope": scopes,
        "response_type": "code",  # <--- Explicitly adding the missing parameter
    }
    
    # Full URL: https://accounts.google.com/o/oauth2/v2/auth?scope=...&response_type=code...
    full_auth_uri = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    # 4. Construct Payload
    payload = {
        "name": f"projects/{env.project_id}/locations/{env.location}/authorizations/{auth_id}",
        "serverSideOauth2": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "authorizationUri": full_auth_uri, # Using the manually built URL
            "tokenUri": "https://oauth2.googleapis.com/token",
            "pkceEnabled": True
        },
    }

    print(f"\n🔐 Configuring BigQuery Authorization: {auth_id}")
    print(f"📍 Create Endpoint: {create_url}")

    async with httpx.AsyncClient() as client:
        # STEP A: Try to DELETE existing one first (Clean Slate)
        # This prevents 409 "Already Exists" and 404 "Update failed" errors.
        try:
            print("🗑️  Checking for existing authorization to clean up...")
            del_resp = await client.delete(resource_url, headers=headers, timeout=10.0)
            if del_resp.status_code == 200:
                print("   - Existing authorization deleted.")
            else:
                print(f"   - No existing authorization found (Status {del_resp.status_code}). Proceeding...")
        except Exception:
            print("   - Cleanup check skipped or failed. Proceeding to create.")

        # STEP B: CREATE (POST)
        try:
            response = await client.post(
                create_url, headers=headers, json=payload, timeout=30.0
            )
            response.raise_for_status()
            print(f"✅ Authorization resource '{auth_id}' created successfully!")
            print(f"📄 Response Scopes count: {len(response.json().get('serverSideOauth2', {}).get('scopes', []))}")
            
        except httpx.HTTPStatusError as err:
            print(f"❌ 🌐 HTTP error occurred: {err}")
            print(f"Response content: {err.response.text}")
            # If POST fails, we try PATCH as a fallback just in case
            if err.response.status_code == 409:
                print("⚠️  Resource exists (409). Attempting PATCH update...")
                patch_params = {"updateMask": "serverSideOauth2.authorizationUri,serverSideOauth2.tokenUri,serverSideOauth2.clientId,serverSideOauth2.clientSecret"}
                patch_resp = await client.patch(resource_url, headers=headers, json=payload, params=patch_params)
                if patch_resp.status_code == 200:
                     print("✅ Authorization UPDATED successfully via fallback!")


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