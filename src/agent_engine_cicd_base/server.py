"""FastAPI server module for ADK agents.

This module provides a FastAPI server for ADK agents with comprehensive observability
features using custom OpenTelemetry setup. Includes an optional ADK web interface for
interactive agent testing.

The custom observability setup coexists with ADK's internal telemetry infrastructure,
enabling simultaneous ADK web UI traces and Google Cloud observability.
"""

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

from .deployment import initialize_environment
from .deployment.config import RunLocalEnv
from .utils import configure_otel_resource, setup_opentelemetry

# Load and validate environment configuration
env = initialize_environment(RunLocalEnv)

# Configure OpenTelemetry resource attributes environment variable
configure_otel_resource(
    agent_name=env.agent_name,
    project_id=env.google_cloud_project,
)

AGENT_DIR = os.getenv("AGENT_DIR", str(Path(__file__).resolve().parent.parent))
SESSION_DB_URL = "sqlite:///./sessions.db"
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8000"]
SERVE_WEB_INTERFACE = True

# ADK fastapi app will set up OTel using resource attributes from env vars
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_DB_URL,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)


def main() -> None:
    """Run the FastAPI server with comprehensive observability.

    Starts the ADK agent server with full OpenTelemetry observability using
    custom setup for trace correlation and Google Cloud export. Features include:
    - Environment variable loading and validation
    - Custom OpenTelemetry setup with trace correlation and Google Cloud export
    - Optional ADK web interface for interactive agent testing
    - Session management with SQLite backend
    - Cloud trace and log export
    - CORS configuration

    The custom observability setup coexists with ADK's internal telemetry,
    providing both ADK web UI traces and Google Cloud observability simultaneously.

    The server runs on the configured host and port with the ADK web interface
    (when enabled), providing interactive agent testing with full observability
    capabilities.

    Environment Variables:
        AGENT_DIR: Path to agent source directory (default: auto-detect from __file__)
        AGENT_NAME: Unique service identifier (required for observability)
        GOOGLE_CLOUD_PROJECT: GCP Project ID for trace and log export
        LOG_LEVEL: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        PORT: Server port (default: 8000)
    """
    # Add our Cloud exporters and logging to ADK's TracerProvider
    setup_opentelemetry(project_id=env.google_cloud_project)

    uvicorn.run(app, host="localhost", port=int(os.environ.get("PORT", 8000)))

    return


if __name__ == "__main__":
    main()
