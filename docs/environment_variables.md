# Environment Variables Reference

This guide provides comprehensive documentation for all environment variables used in this project. All environment variables should be configured in your `.env` file for local development. Terraform also reads the values from your local `.env` file to provision GitHub Actions variables for CI/CD configuration.

## Quick Reference

| Variable | Required | Default | Used For |
|----------|----------|---------|----------|
| [AGENT_NAME](#agent_name) | Yes | - | All operations |
| [GOOGLE_CLOUD_PROJECT](#google_cloud_project) | Yes | - | All operations |
| [GOOGLE_CLOUD_LOCATION](#google_cloud_location) | Yes | - | All operations |
| [GOOGLE_CLOUD_STORAGE_BUCKET](#google_cloud_storage_bucket) | Yes | - | Deployment |
| [GOOGLE_GENAI_USE_VERTEXAI](#google_genai_use_vertexai) | Yes | - | All operations |
| [GITHUB_REPO_NAME](#github_repo_name) | CI/CD only | - | Terraform setup |
| [GITHUB_REPO_OWNER](#github_repo_owner) | CI/CD only | - | Terraform setup |
| [GCS_DIR_NAME](#gcs_dir_name) | No | `agent-engine-staging` | Deployment |
| [AGENT_DISPLAY_NAME](#agent_display_name) | No | `ADK Agent` | Deployment & Agentspace |
| [AGENT_DESCRIPTION](#agent_description) | No | `ADK Agent` | Deployment & Agentspace |
| [AGENT_ENGINE_ID](#agent_engine_id) | Conditional | - | Updates & Agentspace |
| [LOG_LEVEL](#log_level) | No | `INFO` | All operations |
| [OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT](#otel_instrumentation_genai_capture_message_content) | No | `true` | Observability |
| [PORT](#port) | No | `8000` | Local development |
| [ROOT_AGENT_MODEL](#root_agent_model) | No | `gemini-2.5-flash` | Agent runtime |
| [API_VERSION](#api_version) | No | `v1alpha` | Agentspace |
| [AGENTSPACE_APP_ID](#agentspace_app_id) | Agentspace only | - | Agentspace registration |
| [AGENTSPACE_APP_LOCATION](#agentspace_app_location) | Agentspace only | - | Agentspace registration |
| [ADK_SUPPRESS_EXPERIMENTAL_FEATURE_WARNINGS](#adk_suppress_experimental_feature_warnings) | No | `false` | Agent runtime |

## Core Configuration

### AGENT_NAME

**Required:** Yes
**Used by:** All operations
**Example:** `"my-weather-agent"`

Unique identifier for your agent instance. Used for:
- OpenTelemetry service name
- Google Cloud resource naming
- Log identification in Cloud Logging (`{AGENT_NAME}-otel-logs`)
- Terraform resource naming
- Service account naming (`{AGENT_NAME}-app`, `{AGENT_NAME}-cicd`)

**Naming requirements:**
- Must be unique within your project
- Use lowercase letters, numbers, and hyphens only for consistent cloud resource naming conventions
- Should be descriptive of your agent's purpose

> [!IMPORTANT]
> `AGENT_NAME` should closely match (replacing underscores with hyphens) the `root_agent` name hard-coded in the main `agent.py` module for consistent cloud resource observability.
> For example, when the `root_agent` is named `my_weather_agent`, set the `AGENT_NAME` environment variable to `my-weather-agent`

### GOOGLE_CLOUD_PROJECT

**Required:** Yes
**Used by:** All operations
**Example:** `"my-gcp-project-id"`

Your Google Cloud Platform project ID where the agent will be deployed and resources will be created.

**Used for:**
- Vertex AI Agent Engine deployment
- Cloud Trace export
- Cloud Logging export
- Service account creation
- API enablement

### GOOGLE_CLOUD_LOCATION

**Required:** Yes
**Used by:** All operations
**Example:** `"us-central1"`

The Google Cloud region where your Agent Engine instance will be deployed.

**Common values:**
- `us-central1` (Iowa)
- `us-east1` (South Carolina)
- `europe-west1` (Belgium)
- `asia-northeast1` (Tokyo)

> [!NOTE]
> Must be a [supported Vertex AI region](https://cloud.google.com/vertex-ai/docs/general/locations).

### GOOGLE_CLOUD_STORAGE_BUCKET

**Required:** Yes (for deployment)
**Used by:** Deployment
**Example:** `"my-agent-staging-bucket"`

Google Cloud Storage bucket name for staging agent code during deployment. The deployment script will automatically create this bucket if it doesn't exist.

**Bucket configuration:**
- Uniform bucket-level access enabled
- Public access prevention enforced
- Created in the region specified by `GOOGLE_CLOUD_LOCATION` (if provided) or US multi-region (default)

### GOOGLE_GENAI_USE_VERTEXAI

**Required:** Yes
**Used by:** All operations
**Valid values:** `"true"`, `"1"`, `"yes"`

Enables Vertex AI usage for the Google Generative AI SDK. Must be set to a truthy value for deployment to Agent Engine.

## CI/CD Configuration

### GITHUB_REPO_NAME

**Required:** Yes (for CI/CD setup)
**Used by:** Terraform
**Example:** `"my-agent-repo"`

Your GitHub repository name. Used by Terraform to configure GitHub Actions secrets and variables.

> [!NOTE]
> Only required when setting up CI/CD with Terraform. Not needed for manual deployments.

### GITHUB_REPO_OWNER

**Required:** Yes (for CI/CD setup)
**Used by:** Terraform
**Example:** `"my-github-username"` or `"my-org"`

Your GitHub username or organization name. Used by Terraform to identify your repository.

> [!NOTE]
> Only required when setting up CI/CD with Terraform. Not needed for manual deployments.

## Optional Deployment Configuration

### GCS_DIR_NAME

**Required:** No
**Default:** `"agent-engine-staging"`
**Used by:** Deployment
**Example:** `"my-staging-dir"`

Directory name within your staging bucket where agent code will be uploaded during deployment.

**Use case:** Helpful for organizing multiple agents within a single staging bucket.

### AGENT_DISPLAY_NAME

**Required:** No
**Default:** `"ADK Agent"`
**Used by:** Deployment, Agentspace registration
**Example:** `"Weather Assistant"`

Human-readable display name for your agent. Shown in:
- Vertex AI Agent Engine console
- Agentspace Agent Gallery
- Agent registration listings

### AGENT_DESCRIPTION

**Required:** No
**Default:** `"ADK Agent"`
**Used by:** Deployment, Agentspace registration
**Example:** `"Provides weather forecasts and current conditions for cities worldwide"`

Detailed description of your agent's capabilities. Shown in:
- Vertex AI Agent Engine console
- Agentspace Agent Gallery
- Agent registration listings

### AGENT_ENGINE_ID

**Required:** Conditional
**Used by:** Updates, deletion, Agentspace registration
**Example:** `"1234567890123456789"`

The unique identifier of an existing Agent Engine instance.

**When required:**
- Updating an existing agent deployment (instead of creating new instances)
- Deleting an Agent Engine instance
- Registering an agent with Agentspace

**How to find:**
- Check deployment logs for output like: `projects/PROJECT_ID/locations/LOCATION/reasoningEngines/1234567890123456789`
- The Agent Engine ID is the final numeric component (`1234567890123456789` in the example above)
- Also visible in Vertex AI console under Agent Engine instances

> [!WARNING]
> Every deployment creates a NEW Agent Engine instance when `AGENT_ENGINE_ID` is unset. You **MUST** update this variable with your deployed Agent Engine instance ID to enable updates and prevent creating new instances. See the [CI/CD setup guide](cicd_setup_github_actions.md#phase-2-enable-agent-engine-updates) for details.

## Observability Configuration

### LOG_LEVEL

**Required:** No
**Default:** `"INFO"`
**Used by:** All operations
**Valid values:** `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`

Controls logging verbosity for the agent application and deployment scripts.

**Recommendations:**
- **Local Development:** `"DEBUG"` for detailed troubleshooting
- **Production Deployment:** `"INFO"` to minimize logging costs
- **Troubleshooting:** `"DEBUG"` temporarily to diagnose issues

**Log output locations:**
- Google Cloud Logging: `{AGENT_NAME}-otel-logs`
- Standard output (local development)

### OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT

**Required:** No
**Default:** `"true"`
**Used by:** Observability instrumentation
**Valid values:** `"true"`, `"false"`

Controls whether LLM message content (prompts and responses) is captured in OpenTelemetry traces.

**When to disable:**
- Sensitive data in prompts/responses
- Compliance requirements
- Reduced trace payload size

**Reference:** [OpenTelemetry GenAI Instrumentation](https://opentelemetry.io/blog/2024/otel-generative-ai/#example-usage)

## Agent Runtime Configuration

### PORT

**Required:** No
**Default:** `8000`
**Used by:** Local development server
**Example:** `"3000"`

Port number for the local development web server (`uv run local-agent`).

> [!NOTE]
> Only affects local development. Deployed agents don't use this setting.

### ROOT_AGENT_MODEL

**Required:** No
**Default:** `"gemini-2.5-flash"`
**Used by:** Agent runtime
**Example:** `"gemini-2.0-pro"`

Override the default model used by the root agent.

**Reference:** [Gemini model documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models)

### ADK_SUPPRESS_EXPERIMENTAL_FEATURE_WARNINGS

**Required:** No
**Default:** `false`
**Used by:** Agent runtime
**Valid values:** `"true"`, `"false"`

Suppress ADK experimental feature warnings during agent execution.

> [!NOTE]
> Only set to `true` if you're intentionally using experimental ADK features and want cleaner logs.

## Agentspace Configuration

### AGENTSPACE_APP_ID

**Required:** Yes (for Agentspace registration)
**Used by:** Agentspace registration
**Example:** `"my-agentspace-app_1234567890"`

The unique identifier of your Agentspace application.

**How to find:**
- Agentspace console: `https://console.cloud.google.com/gen-app-builder`
- Listed in your Agentspace app settings

**Reference:** [Agentspace documentation](https://cloud.google.com/agentspace/docs)

### AGENTSPACE_APP_LOCATION

**Required:** Yes (for Agentspace registration)
**Used by:** Agentspace registration
**Valid values:** `"global"`, `"us"`, `"eu"`

The region for your Agentspace application.

**API endpoints by region:**
- `global`: `discoveryengine.googleapis.com`
- `us`: `us-discoveryengine.googleapis.com`
- `eu`: `eu-discoveryengine.googleapis.com`

### API_VERSION

**Required:** No
**Default:** `"v1alpha"`
**Used by:** Agentspace registration
**Example:** `"v1"`

Discovery Engine API version used for Agentspace registration.

> [!NOTE]
> Use default unless specifically instructed to use a different version for new Agentspace features.

## CI/CD Internal Variables

These variables are automatically managed by the CI/CD pipeline and should not be set manually.

### GCP_ACCESS_TOKEN

**Set by:** GitHub Actions workflow
**Used by:** Agentspace registration in CI/CD

OAuth access token for Google Cloud API authentication. Automatically generated by the GitHub Actions workflow using Workload Identity Federation.

> [!WARNING]
> Never set this manually. Only used during automated CI/CD runs.

### GCP_WORKLOAD_IDENTITY_PROVIDER

**Set by:** Terraform
**Used by:** GitHub Actions authentication

Workload Identity Provider resource name for secure GitHub Actions authentication to Google Cloud.

> [!WARNING]
> Do not set this manually. Automatically configured as a GitHub repository secret by Terraform.

### GCP_SERVICE_ACCOUNT

**Set by:** Terraform
**Used by:** GitHub Actions authentication

Service account email used by GitHub Actions for deployment operations.

> [!WARNING]
> Do not set this manually. Automatically configured as a GitHub repository secret by Terraform.

## Configuration Examples

### Minimal Local Development

```bash
# Required for local testing
AGENT_NAME="my-agent"
GOOGLE_CLOUD_PROJECT="my-project"
GOOGLE_CLOUD_LOCATION="us-central1"
GOOGLE_GENAI_USE_VERTEXAI="true"
```

### Full Deployment Setup

```bash
# Core configuration
AGENT_NAME="weather-assistant"
GOOGLE_CLOUD_PROJECT="my-production-project"
GOOGLE_CLOUD_LOCATION="us-central1"
GOOGLE_CLOUD_STORAGE_BUCKET="my-agent-staging"
GOOGLE_GENAI_USE_VERTEXAI="true"

# Optional deployment settings
GCS_DIR_NAME="weather-agent-staging"
AGENT_DISPLAY_NAME="Weather Assistant"
AGENT_DESCRIPTION="Provides weather forecasts and current conditions"

# Production observability settings
LOG_LEVEL="INFO"
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="true"
```

### CI/CD with Agentspace

```bash
# Core configuration
AGENT_NAME="weather-assistant"
GOOGLE_CLOUD_PROJECT="my-production-project"
GOOGLE_CLOUD_LOCATION="us-central1"
GOOGLE_CLOUD_STORAGE_BUCKET="my-agent-staging"
GOOGLE_GENAI_USE_VERTEXAI="true"

# GitHub repository (for Terraform)
GITHUB_REPO_NAME="my-agent-repo"
GITHUB_REPO_OWNER="my-github-username"

# Agent Engine instance (after first deployment)
AGENT_ENGINE_ID="1234567890123456789"

# Agentspace integration
AGENTSPACE_APP_ID="my-agentspace-app_1234567890"
AGENTSPACE_APP_LOCATION="global"

# Display settings
AGENT_DISPLAY_NAME="Weather Assistant"
AGENT_DESCRIPTION="Provides weather forecasts and current conditions"

# Observability
LOG_LEVEL="INFO"
```

## Validation

### Test Deployment Configuration

Validate your deployment environment variables without actually deploying:

```bash
uv run test-deploy
```

This checks that all required variables for deployment are set correctly.

### Test Agentspace Configuration

Validate your Agentspace registration environment variables:

```bash
uv run test-register
```

This checks that all required variables for Agentspace registration are set correctly.

## Related Documentation

- **[Development Guide](development.md)** - Development commands and workflows
- **[CI/CD Setup](cicd_setup_github_actions.md)** - Automated deployment configuration
- **[Agentspace Registration](agentspace_registration.md)** - Connecting agents to Agentspace
- **[Observability](observability.md)** - OpenTelemetry instrumentation details
- **[.env.example](../.env.example)** - Environment template file

**[← Back to Documentation](../README.md#documentation)**
