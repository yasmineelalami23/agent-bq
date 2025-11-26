"""Module for storing and retrieving agent instructions.

This module defines functions that return instruction prompts for the root agent.
These instructions guide the agent's behavior, workflow, and tool usage.
"""

from datetime import date

from google.adk.agents.readonly_context import ReadonlyContext


def return_instructions_root() -> str:
    """Return the instruction prompt for the root agent.

    Returns:
        str: The formatted instruction prompt text that defines the agent's
            capabilities and behavior for handling weather and time queries.
    """

    instruction_prompt_root = """

    Answer the user's questions about the time and weather in a city.
    """
    return instruction_prompt_root


def return_global_instruction(ctx: ReadonlyContext) -> str:
    """Generate global instruction with current date.

    Uses InstructionProvider pattern to ensure date updates at request time.

    Args:
        ctx: ReadonlyContext providing access to session state and metadata.

    Returns:
        str: Global instruction string with dynamically generated current date.
    """
    return f"You are a helpful Assistant.\nToday's date: {date.today()}"
