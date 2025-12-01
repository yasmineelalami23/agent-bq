"""ADK LlmAgent configuration."""

import os

from google.adk.agents import LlmAgent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from .callbacks import LoggingCallbacks
from .prompt import return_global_instruction, return_instructions_root
from .tools import get_oanda_pricing
import google.auth

logging_callbacks = LoggingCallbacks()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "search-ahmed")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "yelalami_bq_agent")
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = PROJECT_ID

credentials, _ = google.auth.default()
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)
credentials_config = BigQueryCredentialsConfig(credentials=credentials)
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config, bigquery_tool_config=tool_config
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
