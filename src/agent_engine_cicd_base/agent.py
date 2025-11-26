"""ADK LlmAgent configuration."""

import os

from google.adk.agents import LlmAgent

from .callbacks import LoggingCallbacks
from .prompt import return_global_instruction, return_instructions_root
from .tools import get_current_time, get_weather

logging_callbacks = LoggingCallbacks()

root_agent = LlmAgent(
    name="weather_time_agent",
    description="Agent to answer questions about the time and weather in a city",
    before_agent_callback=logging_callbacks.before_agent,
    after_agent_callback=logging_callbacks.after_agent,
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"),
    instruction=return_instructions_root(),
    global_instruction=return_global_instruction,
    tools=[get_weather, get_current_time],
    before_model_callback=logging_callbacks.before_model,
    after_model_callback=logging_callbacks.after_model,
    before_tool_callback=logging_callbacks.before_tool,
    after_tool_callback=logging_callbacks.after_tool,
)
