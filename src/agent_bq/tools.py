"""Weather and time utility tools for the agent.

This module provides tool functions for retrieving weather information and current time
for specified cities. Currently supports New York as a demonstration, with extensible
architecture for additional locations.
"""

import datetime
import logging
from zoneinfo import ZoneInfo       # <--- ADD THIS
import requests

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


def get_oanda_pricing(instruments: str, account_id: str, api_token: str) -> dict:
    """
    Retrieves real-time pricing for specific financial instruments from OANDA.
    """
    
    # Check if keys are missing (Basic validation)
    if not account_id or not api_token:
        return {"error": "Missing user credentials (Account ID or Token)."}

    # Define the Endpoint
    base_url = "https://api-fxpractice.oanda.com" 
    endpoint = f"{base_url}/v3/accounts/{account_id}/pricing"

    # Set Headers using the passed argument
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    params = {
        "instruments": instruments
    }

    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}