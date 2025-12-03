"""Agent registration module for BigQuery ADK Agent with Google Cloud Discovery Engine Agentspace.

This module handles the registration of deployed BigQuery Agent Engine instances with
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
from dotenv import load_dotenv
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import Request
from pydantic import BaseModel, Field

load_dotenv()

# Required environment variables
try:
    PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
    LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
    AGENT_ENGINE_ID = os.environ["AGENT_ENGINE_ID"]
    AGENTSPACE_APP_ID = os.environ["AGENTSPACE_APP_ID"]
    AGENTSPACE_APP_LOCATION = os.environ["AGENTSPACE_APP_LOCATION"]

except KeyError as e:
    print(f"❌ Missing required environment variable: {e}")
    print("Please ensure the following variables are set:")
    print("- GOOGLE_CLOUD_PROJECT")
    print("- GOOGLE_CLOUD_LOCATION")
    print("- AGENT_ENGINE_ID")
    print("- AGENTSPACE_APP_ID")
    print("- AGENTSPACE_APP_LOCATION")
    exit(1)

# Optional environment variables
API_VERSION = os.getenv("API_VERSION", "v1alpha")
AGENT_DISPLAY_NAME = os.getenv("AGENT_DISPLAY_NAME", "BigQuery Analytics Agent")
AGENT_DESCRIPTION = os.getenv(
    "AGENT_DESCRIPTION",
    "AI-powered agent for querying and analyzing BigQuery datasets"
)

# Construct the Reasoning Engine ID
REASONING_ENGINE = (
    f"projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"
)

# Construct the API Endpoint
if AGENTSPACE_APP_LOCATION == "global":
    SERVER = "discoveryengine.googleapis.com"
else:
    SERVER = f"{AGENTSPACE_APP_LOCATION}-discoveryengine.googleapis.com"

ENDPOINT = (
    f"https://{SERVER}/{API_VERSION}/projects/{PROJECT}/locations/{AGENTSPACE_APP_LOCATION}/"
    f"collections/default_collection/engines/{AGENTSPACE_APP_ID}/assistants/default_assistant/agents"
)

print("\n\n✅ Environment variables set for BigQuery Agent registration:\n")
print(f"PROJECT:                 {PROJECT}")
print(f"LOCATION:                {LOCATION}")
print(f"API_VERSION:             {API_VERSION}")
print(f"AGENTSPACE_APP_ID:       {AGENTSPACE_APP_ID}")
print(f"AGENTSPACE_APP_LOCATION: {AGENTSPACE_APP_LOCATION}")
print(f"AGENT_ENGINE_ID:         {AGENT_ENGINE_ID}")
print(f"AGENT_DISPLAY_NAME:      {AGENT_DISPLAY_NAME}")
print(f"AGENT_DESCRIPTION:       {AGENT_DESCRIPTION}")
print(f"REASONING_ENGINE:        {REASONING_ENGINE}")
print(f"ENDPOINT:                {ENDPOINT}\n\n")


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
    return


def setup_environment() -> dict[str, str]:
    """Set up the registration environment and return authenticated headers.

    Handles:
    - Google Cloud authentication with default credentials
    - Request headers preparation
    - API endpoint logging

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
            credentials, _ = google.auth.default()
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
        "X-Goog-User-Project": PROJECT,
    }

    return headers


async def get_agents_data(headers: dict[str, str]) -> AgentsResponse:
    """Return the agents registered with an Agentspace app.

    Args:
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
            response = await client.get(ENDPOINT, headers=headers, timeout=30.0)
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


async def register() -> None:
    """Register the BigQuery agent with the Agentspace App.

    Handles the complete registration workflow including:
    - Environment variable validation
    - Google Cloud authentication with default credentials
    - Discovery Engine API endpoint construction
    - Duplicate registration detection
    - Agent registration via REST API
    - Optional OAuth authorization configuration

    Raises:
        KeyError: If required environment variables are missing.
        DefaultCredentialsError: If Google Cloud authentication fails.
        SystemExit: If environment validation or authentication fails.
    """
    headers: dict[str, str] = setup_environment()
    agents_data: AgentsResponse = await get_agents_data(headers=headers)

    # Check if the AGENT_ENGINE_ID is already registered
    existing_agent: Agent | None = next(
        (
            agent
            for agent in agents_data.agents
            if agent.agent_engine_id == AGENT_ENGINE_ID
        ),
        None,
    )

    if existing_agent:
        print(f"🤖 BigQuery Agent {AGENT_ENGINE_ID} is already registered, skipping ...")
        return
    else:
        print(f"📭 BigQuery Agent {AGENT_ENGINE_ID} not found, registering...")

    # Check if OAuth is configured (for external service integrations)
    oauth_client_id = os.getenv("OAUTH_CLIENT_ID", "")
    oauth_client_secret = os.getenv("OAUTH_CLIENT_SECRET", "")
    auth_id = os.getenv("AUTH_ID", "")  # Authorization resource ID

    # Prepare the Agent definition JSON Payload for BigQuery agent
    payload: dict[str, Any] = {
        "displayName": AGENT_DISPLAY_NAME,
        "description": AGENT_DESCRIPTION,
        "adk_agent_definition": {
            "tool_settings": {
                "tool_description": AGENT_DESCRIPTION,
            },
            "provisioned_reasoning_engine": {
                "reasoning_engine": REASONING_ENGINE,
            },
        },
    }

    # Add OAuth authorization if configured
    # For Agentspace-level OAuth, we need to reference the Authorization resource
    if oauth_client_id and oauth_client_secret and auth_id:
        print("🔐 OAuth credentials detected")
        print(f"ℹ️  Using Authorization ID: {auth_id}")
        print("ℹ️  Agentspace will handle OAuth flow with Authorization resource")

        # Get project number (required for authorization resource path)
        try:
            import subprocess

            result = subprocess.run(
                [
                    "gcloud",
                    "projects",
                    "describe",
                    PROJECT,
                    "--format=value(projectNumber)",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            project_number = result.stdout.strip()

            if project_number:
                # Add authorization resource reference
                # Use the same location as the authorization resource (typically 'global')
                auth_resource_location = os.getenv("AUTH_LOCATION", "global")
                auth_resource_path = f"projects/{project_number}/locations/{auth_resource_location}/authorizations/{auth_id}"
                payload["adk_agent_definition"]["authorizations"] = [auth_resource_path]
                print(f"✅ Authorization resource path: {auth_resource_path}")
            else:
                print(
                    "⚠️  Warning: Could not get project number, skipping authorization reference"
                )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"⚠️  Warning: Could not get project number: {e}")
            print("⚠️  Skipping authorization reference in payload")
    elif oauth_client_id or oauth_client_secret or auth_id:
        print("⚠️  OAuth partially configured - missing required variables:")
        if not oauth_client_id:
            print("   - OAUTH_CLIENT_ID")
        if not oauth_client_secret:
            print("   - OAUTH_CLIENT_SECRET")
        if not auth_id:
            print("   - AUTH_ID")
        print("ℹ️  Agent will use service account authentication")
    else:
        print("ℹ️  OAuth not configured, agent will use service account authentication")

    print(f"\n📦 Payload:\n{json.dumps(payload, indent=2)}\n")

    # Register the Agent
    print(f"🔗 Registering BigQuery Agent: {AGENT_DISPLAY_NAME}...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ENDPOINT, headers=headers, json=payload, timeout=30.0
            )
            response.raise_for_status()
            print("✅ BigQuery Agent registered successfully!")
            print("📊 Your agent can now query and analyze BigQuery datasets")
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

    return


async def unregister() -> None:
    """Unregister the BigQuery agent from the Agentspace App.

    Finds and removes the agent registration based on AGENT_ENGINE_ID.
    Prompts for user confirmation before proceeding to unregister.

    Raises:
        SystemExit: If user cancels the unregister operation or if it fails.
    """
    headers: dict[str, str] = setup_environment()
    agents_data: AgentsResponse = await get_agents_data(headers=headers)

    # Find the agent to unregister
    agent_to_unregister: Agent | None = next(
        (
            agent
            for agent in agents_data.agents
            if agent.agent_engine_id == AGENT_ENGINE_ID
        ),
        None,
    )

    # Exit if the AGENT_ENGINE_ID is not registered
    if not agent_to_unregister:
        print(
            f"❌ 📭 BigQuery Agent Engine ID '{AGENT_ENGINE_ID}' is not currently"
            " registered with Agentspace"
        )
        return

    # Confirmation prompt
    response = input(
        f"🤔 Unregister BigQuery Agent '{agent_to_unregister.display_name}' with Agent Engine ID"
        f" '{AGENT_ENGINE_ID}' from Agentspace app '{AGENTSPACE_APP_ID}'? [y/N]: "
    )
    if response.lower() not in ["y", "yes"]:
        print("❌ Unregister operation cancelled")
        return

    # Construct DELETE endpoint for the specific agent
    delete_endpoint = f"{ENDPOINT}/{agent_to_unregister.registration_id}"

    # Unregister the agent
    try:
        print(f"🔓 Unregistering BigQuery agent {AGENT_ENGINE_ID}...")
        async with httpx.AsyncClient() as client:
            http_response = await client.delete(
                delete_endpoint, headers=headers, timeout=30.0
            )
            http_response.raise_for_status()
            print(
                f"✅ BigQuery Agent {AGENT_ENGINE_ID} unregistered successfully from Agentspace"
            )
    except httpx.HTTPStatusError as err:
        print(f"❌ 🌐 HTTP error during unregister operation: {err}")
        print(f"Response content: {err.response.text}")
        exit(1)
    except httpx.RequestError as err:
        print(f"❌ ⚠️ Error during unregister operation: {err}")
        exit(1)

    return


async def create_authorization() -> None:
    """Create an Authorization resource for OAuth in Agentspace.

    This function creates a server-side OAuth authorization resource that can be
    referenced by agents for OAuth authentication with external services.

    Required environment variables:
        - GOOGLE_CLOUD_PROJECT: GCP project ID
        - AUTH_ID: Unique identifier for this authorization resource
        - OAUTH_CLIENT_ID: OAuth client ID
        - OAUTH_CLIENT_SECRET: OAuth client secret
        - OAUTH_AUTH_URI: OAuth authorization endpoint
        - OAUTH_TOKEN_URI: OAuth token endpoint

    Optional environment variables:
        - OAUTH_SCOPES: Space-separated list of OAuth scopes
        - OAUTH_AUDIENCE: OAuth audience parameter
        - OAUTH_PROMPT: OAuth prompt parameter (e.g., 'consent')
        - AUTH_LOCATION: Location for authorization resource (defaults to 'global')

    Raises:
        SystemExit: If required environment variables are missing or request fails.
    """
    # Check for required environment variables
    auth_id = os.getenv("AUTH_ID", "")
    oauth_client_id = os.getenv("OAUTH_CLIENT_ID", "")
    oauth_client_secret = os.getenv("OAUTH_CLIENT_SECRET", "")
    oauth_auth_uri = os.getenv("OAUTH_AUTH_URI", "")
    oauth_token_uri = os.getenv("OAUTH_TOKEN_URI", "")

    if not all([auth_id, oauth_client_id, oauth_client_secret, oauth_auth_uri, oauth_token_uri]):
        print("❌ Missing required environment variables for authorization creation:")
        if not auth_id:
            print("   - AUTH_ID")
        if not oauth_client_id:
            print("   - OAUTH_CLIENT_ID")
        if not oauth_client_secret:
            print("   - OAUTH_CLIENT_SECRET")
        if not oauth_auth_uri:
            print("   - OAUTH_AUTH_URI")
        if not oauth_token_uri:
            print("   - OAUTH_TOKEN_URI")
        exit(1)

    headers: dict[str, str] = setup_environment()

    # Authorization resources are typically at 'global' location
    # Allow override with AUTH_LOCATION env var
    auth_location = os.getenv("AUTH_LOCATION", "global")
    
    print(f"ℹ️  Using authorization location: {auth_location}")
    if auth_location != "global":
        print(f"⚠️  Warning: Authorization resources are typically in 'global' location")
        print(f"⚠️  If this fails, try setting AUTH_LOCATION=global")

    # Construct the authorization endpoint
    location_prefix = "" if auth_location == "global" else f"{auth_location}-"
    auth_endpoint = (
        f"https://{location_prefix}discoveryengine.googleapis.com/{API_VERSION}/"
        f"projects/{PROJECT}/locations/{auth_location}/authorizations"
        f"?authorizationId={auth_id}"
    )

    # Get optional OAuth parameters
    oauth_scopes = os.getenv("OAUTH_SCOPES", "")
    oauth_audience = os.getenv("OAUTH_AUDIENCE", "")
    oauth_prompt = os.getenv("OAUTH_PROMPT", "")

    # Build authorization URL with optional parameters
    params = {
        "response_type": "code",
    }
    
    if oauth_audience:
        params["audience"] = oauth_audience
    if oauth_prompt:
        params["prompt"] = oauth_prompt
    if oauth_scopes:
        params["scope"] = oauth_scopes

    # Construct URL with encoded parameters
    auth_url = f"{oauth_auth_uri}?{urlencode(params)}" if params else oauth_auth_uri

    payload = {
        "name": f"projects/{PROJECT}/locations/{auth_location}/authorizations/{auth_id}",
        "serverSideOauth2": {
            "clientId": oauth_client_id,
            "clientSecret": oauth_client_secret,
            "authorizationUri": auth_url,
            "tokenUri": oauth_token_uri,
        },
    }

    print(f"\n🔐 Creating Authorization resource: {auth_id}")
    print(f"📍 Endpoint: {auth_endpoint}")
    print(f"📦 Payload:\n{json.dumps(payload, indent=2)}\n")

    # Create the authorization resource
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                auth_endpoint, headers=headers, json=payload, timeout=30.0
            )
            response.raise_for_status()
            print(f"✅ Authorization resource '{auth_id}' created successfully!")
            print(f"📄 Response:\n{json.dumps(response.json(), indent=2)}\n")
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


async def delete_authorization() -> None:
    """Delete an Authorization resource from Agentspace.

    Required environment variables:
        - GOOGLE_CLOUD_PROJECT: GCP project ID
        - AUTH_ID: Identifier of the authorization resource to delete

    Optional environment variables:
        - AUTH_LOCATION: Location for authorization resource (defaults to 'global')

    Raises:
        SystemExit: If required environment variables are missing or request fails.
    """
    auth_id = os.getenv("AUTH_ID", "")

    if not auth_id:
        print("❌ Missing required environment variable: AUTH_ID")
        exit(1)

    headers: dict[str, str] = setup_environment()

    # Authorization resources are typically at 'global' location
    auth_location = os.getenv("AUTH_LOCATION", "global")
    
    print(f"ℹ️  Using authorization location: {auth_location}")

    # Construct the authorization endpoint
    location_prefix = "" if auth_location == "global" else f"{auth_location}-"
    auth_endpoint = (
        f"https://{location_prefix}discoveryengine.googleapis.com/{API_VERSION}/"
        f"projects/{PROJECT}/locations/{auth_location}/authorizations/{auth_id}"
    )

    # Confirmation prompt
    response = input(
        f"🤔 Delete Authorization resource '{auth_id}' from project '{PROJECT}'? [y/N]: "
    )
    if response.lower() not in ["y", "yes"]:
        print("❌ Delete authorization operation cancelled")
        return

    print(f"\n🔓 Deleting Authorization resource: {auth_id}")
    print(f"📍 Endpoint: {auth_endpoint}\n")

    # Delete the authorization resource
    try:
        async with httpx.AsyncClient() as client:
            http_response = await client.delete(
                auth_endpoint, headers=headers, timeout=30.0
            )
            http_response.raise_for_status()
            print(f"✅ Authorization resource '{auth_id}' deleted successfully!")
    except httpx.HTTPStatusError as err:
        print(f"❌ 🌐 HTTP error occurred: {err}")
        print(f"Response content: {err.response.text}")
        exit(1)
    except httpx.RequestError as err:
        print(f"❌ ⚠️ Error during delete operation: {err}")
        exit(1)


async def list_agent_registrations() -> None:
    """List all agents registered with the Agentspace App."""
    headers: dict[str, str] = setup_environment()
    agents_data: AgentsResponse = await get_agents_data(headers=headers)

    if not agents_data.agents:
        print("📭 No agents currently registered with the Agentspace app.")
        return

    print("\n📡 Raw response:\n")
    agents_data.print_raw_response()
    print(f"\n🗂️ Agents registered with Agentspace app '{AGENTSPACE_APP_ID}':\n")
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


def main_create_authorization() -> None:
    """Synchronous wrapper for the async create_authorization function."""
    asyncio.run(create_authorization())


def main_delete_authorization() -> None:
    """Synchronous wrapper for the async delete_authorization function."""
    asyncio.run(delete_authorization())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "register":
            main_register()
        elif command == "unregister":
            main_unregister()
        elif command == "list":
            main_list()
        elif command == "create-auth":
            main_create_authorization()
        elif command == "delete-auth":
            main_delete_authorization()
        else:
            print("Usage: python bigquery_agent_register.py [register|unregister|list|create-auth|delete-auth]")
    else:
        print("Usage: python bigquery_agent_register.py [register|unregister|list|create-auth|delete-auth]")