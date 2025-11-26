"""Agent deployment module for Google Cloud Vertex AI Agent Engine.

This module handles deploying agents to Vertex AI Agent Engine, supporting
new deployments and updates to existing agent engine instances.
Includes environment validation, staging bucket validation/creation, wheel package
handling, and Vertex AI integration.
"""

from pathlib import Path

import vertexai
from google.api_core.exceptions import Forbidden, NotFound
from google.cloud import storage
from google.cloud.exceptions import Conflict
from google.cloud.storage import Bucket
from google.genai.errors import ClientError
from vertexai.agent_engines import AdkApp

from .config import DeleteEnv, DeployEnv, initialize_environment


def confirm_or_create_bucket(bucket_name: str, location: str | None = None) -> None:
    """Confirm if staging bucket exists and create if it doesn't.

    Creates buckets with security best practices: uniform bucket-level access
    enabled and public access prevention enforced.

    Args:
        bucket_name: The name of the storage bucket (without gs:// prefix).
        location (optional): The GCP Storage bucket location for bucket creation.
            The storage.Client creates buckets in the "US" multi-region by default.
            ref: https://cloud.google.com/storage/docs/locations

    Raises:
        SystemExit: If bucket creation fails.
    """
    gcs_client = storage.Client()
    bucket: Bucket = gcs_client.bucket(bucket_name)

    try:
        bucket.reload()
        print(f"✅ Staging bucket '{bucket_name}' exists")

    except NotFound:
        # Bucket doesn't exist (HTTP 404), try to create it
        location_msg = f" in location '{location}'" if location else ""
        print(f"🪄 Creating staging bucket '{bucket_name}'{location_msg}...")
        try:
            gcs_client.create_bucket(bucket, location=location)
            bucket.iam_configuration.uniform_bucket_level_access_enabled = True
            bucket.iam_configuration.public_access_prevention = "enforced"
            bucket.patch()
            print(f"✅ Staging bucket '{bucket_name}' created successfully")

        except Conflict:
            print(f"⚠️ Bucket '{bucket_name}' already exists. Continuing...")

        except Exception as e:
            print(f"\n❌ 🪣 Failed to create staging bucket '{bucket_name}': {e}")
            print("Please check the error and try again")
            exit(1)

    except Forbidden as e:
        # Permission denied (HTTP 403)
        print(f"\n❌ 🔒 Permission denied accessing bucket '{bucket_name}': {e}")
        print("Please check your Google Cloud Storage permissions:")
        print("  - storage.buckets.get (to confirm bucket exists)")
        print("  - storage.buckets.create (to create bucket if needed)")
        print("  - storage.buckets.update (to configure bucket security settings)")
        exit(1)

    except Exception as e:
        # Other unexpected errors
        print(f"\n❌ ⚠️ Unexpected error confirming bucket '{bucket_name}': {e}")
        print("Please check the error and try again")
        exit(1)


def get_wheel_file() -> Path:
    """Get the first .whl file in the current directory.

    Returns:
        Path object of the .whl file.

    Raises:
        FileNotFoundError: If no .whl file is found in the current directory.
    """
    print(f"📂 Path: {Path().cwd()}")
    wheel_file = next(Path().glob("*.whl"), None)
    if wheel_file is None:
        raise FileNotFoundError(
            "\n❌ 🔍 No .whl file found. Run 'uv build --wheel --out-dir .' "
            "to generate the wheel file."
        )
    print(f"📦 Wheel file name: {wheel_file.name}")
    return wheel_file


def delete_wheel_file(wheel_file: Path) -> None:
    """Delete the specified wheel file.

    Args:
        wheel_file: Path object of the .whl file to delete.

    Returns:
        None
    """
    try:
        wheel_file.unlink()
        print(f"🧹 Removed local wheel file: {wheel_file.name}")
    except FileNotFoundError:
        print(f"\n❌ 🔍 Wheel file not found: {wheel_file.name}")
    except Exception as e:
        print(f"\n❌ ⚠️ Error removing wheel file: {wheel_file.name}: {e}")

    return


def test_environment() -> None:
    """Test function to validate the deployment environment.

    Displays the loaded environment variables and the presence of a wheel file.
    """
    _ = initialize_environment(DeployEnv)

    try:
        _ = get_wheel_file()
    except FileNotFoundError as e:
        print(e)

    return


def deploy() -> None:
    """Deploy the application to Agent Engine.

    Handles the complete deployment workflow including:
    - Environment variable validation
    - Wheel package discovery and validation
    - Agent Engine creation or update based on AGENT_ENGINE_ID
    - Custom telemetry setup with enhanced observability

    Uses an `instrumentor_builder` callable to ensure comprehensive
    OpenTelemetry instrumentation in the deployed Agent Engine environment.

    Environment Variables:
        See DeployEnv model for required and optional configuration.

    Raises:
        FileNotFoundError: If no wheel package is found in the current directory.
        SystemExit: If deployment fails.
    """
    # Lazy load the root_agent
    from ..agent import root_agent
    from ..utils import setup_opentelemetry

    # Load and validate environment configuration
    env = initialize_environment(DeployEnv)

    # Confirm or create staging bucket
    confirm_or_create_bucket(env.google_cloud_storage_bucket)

    # Initialize Vertex AI client
    client = vertexai.Client(
        project=env.google_cloud_project,
        location=env.google_cloud_location,
    )  # pyright: ignore[reportCallIssue]

    try:
        wheel_file = get_wheel_file()
    except FileNotFoundError as e:
        print(e)
        exit(1)

    # Use wheel file instead of hardcoded dependencies
    requirements = [wheel_file.name]
    extra_packages = [wheel_file.name]

    adk_app = AdkApp(
        agent=root_agent,
        enable_tracing=True,
        instrumentor_builder=setup_opentelemetry,
    )

    try:
        if env.agent_engine_id:
            print(f"🔄 Updating agent engine {env.agent_engine_id}...")
            remote_agent = client.agent_engines.update(
                name=(
                    f"projects/{env.google_cloud_project}/"
                    f"locations/{env.google_cloud_location}/"
                    f"reasoningEngines/{env.agent_engine_id}"
                ),
                agent=adk_app,
                config={
                    "staging_bucket": f"gs://{env.google_cloud_storage_bucket}",
                    "requirements": requirements,
                    "extra_packages": extra_packages,
                    "gcs_dir_name": env.gcs_dir_name,
                    "display_name": env.agent_display_name,
                    "description": env.agent_description,
                    "env_vars": env.agent_env_vars,
                    "service_account": env.service_account,
                },
            )
            print(f"🤖 Updated agent engine resource: {remote_agent.api_resource.name}")
        else:
            print("🪄 Creating new agent engine...")
            remote_agent = client.agent_engines.create(
                agent=adk_app,
                config={
                    "staging_bucket": f"gs://{env.google_cloud_storage_bucket}",
                    "requirements": requirements,
                    "extra_packages": extra_packages,
                    "gcs_dir_name": env.gcs_dir_name,
                    "display_name": env.agent_display_name,
                    "description": env.agent_description,
                    "env_vars": env.agent_env_vars,
                    "service_account": env.service_account,
                },
            )
            print(f"🤖 Created agent engine resource: {remote_agent.api_resource.name}")
    except ValueError as e:
        print(f"\n❌ ⚠️ Invalid deployment parameter: {e}")
        exit(1)

    except FileNotFoundError as e:
        print(f"\n❌ 🔍 Required file not found: {e}")
        exit(1)

    except OSError as e:
        print(f"\n❌ 📄 Requirements file error: {e}")
        print("Check that the requirements file exists and is accessible")
        exit(1)

    except KeyboardInterrupt:
        print("\n❌ Deployment cancelled by user")
        exit(1)

    except Exception as e:
        operation = "updating" if env.agent_engine_id else "creating"
        print(f"\n❌ ⚠️ Unexpected error {operation} agent engine: {e}")
        exit(1)

    finally:
        delete_wheel_file(wheel_file)

    operation = "updated" if env.agent_engine_id else "created"
    print(f"✅ Agent engine {operation} successfully")

    return


def delete() -> None:
    """Delete an Agent Engine instance.

    Requires AGENT_ENGINE_ID environment variable to identify the target instance.
    Prompts for user confirmation before proceeding with deletion.

    Raises:
        SystemExit: If AGENT_ENGINE_ID is not provided or user cancels deletion.
    """
    # Load and validate environment configuration
    env = initialize_environment(DeleteEnv)

    # Initialize Vertex AI client
    client = vertexai.Client(
        project=env.google_cloud_project,
        location=env.google_cloud_location,
    )  # pyright: ignore[reportCallIssue]

    # Get the remote agent instance to confirm its display name
    resource_name = (
        f"projects/{env.google_cloud_project}/"
        f"locations/{env.google_cloud_location}/"
        f"reasoningEngines/{env.agent_engine_id}"
    )

    try:
        remote_agent = client.agent_engines.get(name=resource_name)
        agent_display_name = remote_agent.api_resource.display_name
    except ClientError as e:
        print(f"\n❌ ⚠️ Error retrieving agent engine '{env.agent_engine_id}': {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ⚠️ Unexpected error retrieving agent engine: {e}")
        exit(1)

    # Confirmation prompt
    response = input(
        f"🤔 Delete Agent '{agent_display_name}' "
        f"with Agent Engine ID '{env.agent_engine_id}'? [y/N]: "
    )
    if response.lower() not in ["y", "yes"]:
        print("\n❌ Deletion cancelled")
        exit(0)

    try:
        print(f"🗑️ Deleting agent engine {env.agent_engine_id}...")
        client.agent_engines.delete(name=resource_name)
        print(f"✅ Agent engine {env.agent_engine_id} deleted successfully")
    except Exception as e:
        print(f"\n❌ ⚠️ Error deleting agent engine: {e}")
        exit(1)

    return
