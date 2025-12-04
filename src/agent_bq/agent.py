"""ADK LlmAgent configuration with Gemini Enterprise OAuth support."""

import os
from typing import Optional

import google.auth
import google.oauth2.credentials

# 1. Corrected Agent Import
from google.adk.agents import LlmAgent

# 2. Corrected ToolContext Import (Moved from context to tools)
from google.adk.tools import ToolContext

# 3. Corrected BigQuery Imports
# BigQueryCredentialsConfig is now exposed publicly here.
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode

# Local imports
from .callbacks import LoggingCallbacks
from .prompt import return_global_instruction, return_instructions_root
from .tools import get_oanda_pricing

logging_callbacks = LoggingCallbacks()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "search-ahmed")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "yelalami_bq_agent")
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = PROJECT_ID

# Check if OAuth credentials are configured
oauth_client_id = os.getenv("OAUTH_CLIENT_ID")
oauth_client_secret = os.getenv("OAUTH_CLIENT_SECRET")
# ADK 1.19 typically looks for 'bigquery_token_cache' by default. 
# If your environment provides a different key, ensure your deployment config matches.

bigquery_toolset = None

# Initialize credentials based on environment
if oauth_client_id and oauth_client_secret:
    # Use Gemini Enterprise / OAuth Flow
    print("🔐 Configuring BigQuery with OAuth support")
    
    # In ADK 1.19, use the standard BigQueryCredentialsConfig.
    # It handles the client_id/secret and scope logic internally.
    credentials_config = BigQueryCredentialsConfig(
        client_id=oauth_client_id,
        client_secret=oauth_client_secret,
        scopes=[
            "https://www.googleapis.com/auth/bigquery",
            "https://www.googleapis.com/auth/cloud-platform",
        ],
        # If you have specific token cache requirements, check if 
        # BigQueryCredentialsConfig accepts a `token_cache_config` in your specific patch version,
        # otherwise, rely on standard ADK behavior.
    )
    
    bigquery_toolset = BigQueryToolset(
        credentials_config=credentials_config,
        bigquery_tool_config=BigQueryToolConfig(write_mode=WriteMode.BLOCKED),
    )

else:
    # Use service account credentials (for local development)
    print("ℹ️  Configuring BigQuery with service account credentials")
    
    credentials, _ = google.auth.default()
    
    credentials_config = BigQueryCredentialsConfig(credentials=credentials)
    
    bigquery_toolset = BigQueryToolset(
        credentials_config=credentials_config, 
        bigquery_tool_config=BigQueryToolConfig(write_mode=WriteMode.BLOCKED)
    )

strict_instruction = (
    f"You are a helpful assistant. The Google Cloud Project ID is {PROJECT_ID}. "
    f"You are ONLY allowed to query tables in the dataset '{DATASET_ID}'. "
    f"Do not access, list, or query any other datasets. "
    f"Always qualify your table names like `{PROJECT_ID}.{DATASET_ID}.table_name`. "
    f"You can answer questions about BigQuery data and fetch real-time forex pricing from OANDA."
    + return_instructions_root()
)

root_agent = LlmAgent(
    name="bigquery_agent",
    description="Agent to answer questions about BigQuery data and models and execute SQL queries.",
    before_agent_callback=logging_callbacks.before_agent,
    after_agent_callback=logging_callbacks.after_agent,
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"),
    instruction=strict_instruction,
    global_instruction=return_global_instruction,
    tools=[bigquery_toolset, get_oanda_pricing],
    before_model_callback=logging_callbacks.before_model,
    after_model_callback=logging_callbacks.after_model,
    before_tool_callback=logging_callbacks.before_tool,
    after_tool_callback=logging_callbacks.after_tool,
)