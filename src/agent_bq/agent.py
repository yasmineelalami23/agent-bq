"""ADK LlmAgent configuration with Gemini Enterprise OAuth support."""

import os

import google.auth
from google.adk.agents import LlmAgent
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

from .callbacks import LoggingCallbacks
from .credentials import (
    GeminiEnterpriseBigQueryToolset,
    GeminiEnterpriseCredentialsConfig,
)
from .prompt import return_global_instruction, return_instructions_root
from .tools import get_oanda_pricing

# =============================================================================
# Configuration
# =============================================================================

logging_callbacks = LoggingCallbacks()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "search-ahmed")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "yelalami_bq_agent")
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = PROJECT_ID

# =============================================================================
# BigQuery Toolset Setup
# =============================================================================

oauth_client_id = os.getenv("OAUTH_CLIENT_ID")
oauth_client_secret = os.getenv("OAUTH_CLIENT_SECRET")
gemini_enterprise_auth_id = os.getenv("GEMINI_ENTERPRISE_AUTH_ID")

bigquery_toolset: BigQueryToolset | GeminiEnterpriseBigQueryToolset

if oauth_client_id and oauth_client_secret:
    # Use Gemini Enterprise / OAuth Flow
    print("Configuring BigQuery with OAuth support")
    if gemini_enterprise_auth_id:
        print(f"  Gemini Enterprise auth ID: {gemini_enterprise_auth_id}")

    credentials_config = GeminiEnterpriseCredentialsConfig(
        client_id=oauth_client_id,
        client_secret=oauth_client_secret,
        scopes=[
            "https://www.googleapis.com/auth/bigquery",
            "https://www.googleapis.com/auth/cloud-platform",
        ],
        gemini_enterprise_auth_id=gemini_enterprise_auth_id,
    )

    bigquery_toolset = GeminiEnterpriseBigQueryToolset(
        credentials_config=credentials_config,
        bigquery_tool_config=BigQueryToolConfig(write_mode=WriteMode.BLOCKED),
    )

else:
    # Use service account credentials (for local development)
    print("Configuring BigQuery with service account credentials")

    credentials, _ = google.auth.default()

    sa_credentials_config = BigQueryCredentialsConfig(credentials=credentials)

    bigquery_toolset = BigQueryToolset(
        credentials_config=sa_credentials_config,
        bigquery_tool_config=BigQueryToolConfig(write_mode=WriteMode.BLOCKED),
    )

# =============================================================================
# Agent Definition
# =============================================================================

strict_instruction = (
    f"You are a helpful assistant. The Google Cloud Project ID is {PROJECT_ID}. "
    f"You are ONLY allowed to query tables in the dataset '{DATASET_ID}'. "
    f"Do not access, list, or query any other datasets. "
    f"Always qualify your table names like `{PROJECT_ID}.{DATASET_ID}.table_name`. "
    "You can answer questions about BigQuery data and fetch real-time forex "
    "pricing from OANDA." + return_instructions_root()
)

root_agent = LlmAgent(
    name="bigquery_agent",
    description=(
        "Agent to answer questions about BigQuery data and models "
        "and execute SQL queries."
    ),
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"),
    instruction=strict_instruction,
    global_instruction=return_global_instruction,
    tools=[bigquery_toolset, get_oanda_pricing],
    before_agent_callback=logging_callbacks.before_agent,
    after_agent_callback=logging_callbacks.after_agent,
    before_model_callback=logging_callbacks.before_model,
    after_model_callback=logging_callbacks.after_model,
    before_tool_callback=logging_callbacks.before_tool,
    after_tool_callback=logging_callbacks.after_tool,
)
