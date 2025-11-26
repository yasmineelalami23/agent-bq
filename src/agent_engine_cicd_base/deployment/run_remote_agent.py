"""Interactive run script for deployed Agent Engine instances.

This module provides an interactive command-line interface for running deployed
agents in Vertex AI Agent Engine. Supports session management and streaming
responses for real-time conversation testing.
"""

import asyncio
from typing import Any

import vertexai

from .config import RunRemoteEnv, initialize_environment


async def run_interactive_agent() -> None:
    """Main function to test a deployed Agent Engine instance interactively.

    Provides an interactive command-line interface for testing deployed agents.
    Features include:
    - Environment variable validation
    - Vertex AI initialization with staging bucket
    - Agent Engine instance retrieval
    - Interactive session management
    - Streaming response handling
    - Automatic session cleanup on exit

    The function continues until the user types 'quit', at which point it
    gracefully cleans up the session and exits.

    Raises:
        KeyError: If required environment variables are missing.
    """
    # Load and validate environment configuration
    env = initialize_environment(RunRemoteEnv)

    client = vertexai.Client(
        project=env.google_cloud_project,
        location=env.google_cloud_location,
    )  # pyright: ignore[reportCallIssue]

    user_id = "user"
    agent = client.agent_engines.get(
        name=(
            f"projects/{env.google_cloud_project}/"
            f"locations/{env.google_cloud_location}/"
            f"reasoningEngines/{env.agent_engine_id}"
        )
    )
    session: dict[str, Any] = await agent.async_create_session(user_id=user_id)
    print(f"🚀 Initiated session ID: {session['id']}\n")
    print("💡 Type 'quit' to exit.\n")
    while True:
        user_input = input("🦖 User input: ")
        if user_input == "quit":
            break

        async for event in agent.async_stream_query(
            user_id=user_id,
            session_id=session["id"],
            message=user_input,
        ):
            if "content" in event and "parts" in event["content"]:
                parts = event["content"]["parts"]
                for part in parts:
                    if "text" in part:
                        text_part = part["text"]
                        print(f"🤖 AI response: {text_part}")

    print(f"\n🧹 Deleting session ID: {session['id']}...", end="", flush=True)
    await agent.async_delete_session(user_id=user_id, session_id=session["id"])
    print(" Done")

    return


def main() -> None:
    """Entry point for uv script."""
    asyncio.run(run_interactive_agent())
