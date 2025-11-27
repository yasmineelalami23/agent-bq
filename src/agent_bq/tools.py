"""Weather and time utility tools for the agent.

This module provides tool functions for retrieving weather information and current time
for specified cities. Currently supports New York as a demonstration, with extensible
architecture for additional locations.
"""

import datetime
import logging
from zoneinfo import ZoneInfo

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


def get_weather(city: str, tool_context: ToolContext) -> dict:
    """Get the current weather report for a specified city.

    Args:
        city (str): The name of the city for which to retrieve the weather report.
        tool_context (ToolContext): Context for the tool invocation.

    Returns:
        dict: status and result or error msg.
    """
    logger.info(
        f"Getting weather for city: '{city}'...",
        extra={"invocation_id": tool_context.invocation_id},
    )
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": (
                "The weather in New York is sunny with a temperature of 25 degrees"
                " Celsius (77 degrees Fahrenheit)."
            ),
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available.",
        }

def get_current_time(city: str, tool_context: ToolContext) -> dict:
    """Get the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.
        tool_context (ToolContext): Context for the tool invocation.

    Returns:
        dict: status and result or error msg.
    """
    logger.info(
        f"Getting current time for city: '{city}'...",
        extra={"invocation_id": tool_context.invocation_id},
    )
    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {
            "status": "error",
            "error_message": (f"Sorry, I don't have timezone information for {city}."),
        }

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = f"The current time in {city} is {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    return {"status": "success", "report": report}
