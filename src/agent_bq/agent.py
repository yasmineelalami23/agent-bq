"""ADK LlmAgent configuration."""

import os

from google.adk.agents import LlmAgent
from google.adk.tools.bigquery import BigQueryCredentialsConfig
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.tools.bigquery.config import WriteMode
from .callbacks import LoggingCallbacks
from .prompt import return_global_instruction, return_instructions_root
from .tools import get_current_time, get_weather
import google.auth

logging_callbacks = LoggingCallbacks()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "search-ahmed")
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = PROJECT_ID

credentials, _ = google.auth.default()
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)
credentials_config = BigQueryCredentialsConfig(credentials=credentials)
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config, bigquery_tool_config=tool_config
)

root_agent = LlmAgent(
    name="bigquery_agent",
    description="Agent to answer questions about BigQuery data and models and execute SQL queries.",
    before_agent_callback=logging_callbacks.before_agent,
    after_agent_callback=logging_callbacks.after_agent,
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"),
    instruction=f"You are a helpful assistant. The Google Cloud Project ID is {PROJECT_ID}. " + return_instructions_root(),
    global_instruction=return_global_instruction,
    tools=[bigquery_toolset],
    before_model_callback=logging_callbacks.before_model,
    after_model_callback=logging_callbacks.after_model,
    before_tool_callback=logging_callbacks.before_tool,
    after_tool_callback=logging_callbacks.after_tool,
)
