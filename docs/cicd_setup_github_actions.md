# Setup CI/CD with GitHub Actions

This document provides instructions for setting up continuous integration and deployment to Google Agent Engine using GitHub Actions.

## Overview

The CI/CD pipeline automatically deploys the Agent to Vertex AI Agent Engine whenever changes are merged to the `main` branch. It supports custom agent display names and descriptions, and includes optional Agentspace registration.

This setup uses **Terraform** to provision the necessary GitHub configuration and Google Cloud infrastructure, and **GitHub Actions** to handle the deployment pipeline. The Terraform configuration automatically:

- Creates service accounts with appropriate IAM roles
- Sets up Workload Identity Federation for secure GitHub Actions authentication
- Configures GitHub repository secrets and variables
- Enables required Google Cloud APIs

### CI/CD Flow

```
Git commit to main → GitHub Actions → Deploy to Agent Engine → (Optional) Register with Agentspace
```

## Prerequisites

- Terraform installed locally
- GitHub repository with admin access
- The GitHub CLI (`gh`) installed and authenticated
- A Google Cloud project with billing enabled
- Google Cloud CLI (`gcloud`) configured with Owner (`roles/owner`) permission on the deployment project


## Setup Instructions

This setup process has three phases:
1. **Initial Terraform Setup**: Provision infrastructure and deploy your first agent
2. **Enable Agent Engine Updates**: Capture the Agent Engine ID and enable updates to the deployed instance
3. **Ongoing Development**: Iterate on your agent with automated deployments

### Phase 1: Initial Terraform Setup

#### 1. Configure Environment Variables

> [!IMPORTANT]
> Terraform reads configuration from environment variables. Ensure you set these variables in a `.env` file in the project root.

Copy and configure the environment file:

```bash
cp .env.example .env
```

Edit `.env` and configure the required variables:

```bash
# Agent name used as a base for Terraform resource and log names
AGENT_NAME="your-agent-name"

# Google Cloud configuration
GOOGLE_GENAI_USE_VERTEXAI="true"
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"
GOOGLE_CLOUD_STORAGE_BUCKET="your-staging-bucket"
GCS_DIR_NAME="your-agent-engine-staging-directory"

# GitHub repository information
GITHUB_REPO_NAME="your-repo-name"
GITHUB_REPO_OWNER="your-github-username-or-organization"

# Agent application runtime environment variables
LOG_LEVEL="INFO"
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="true"

# Optional variables (leave commented for initial setup)
# AGENT_DISPLAY_NAME="My Agent"
# AGENT_DESCRIPTION="This is my AI agent"
# AGENT_ENGINE_ID=""  # get this from initial deployment logs
# AGENTSPACE_APP_ID=""
# AGENTSPACE_APP_LOCATION="global"
```

> [!WARNING]
> Set `LOG_LEVEL=INFO` for production deployments to minimize logging verbosity and costs.

#### 2. Initialize and Apply Terraform

Initialize Terraform in the `terraform` directory:

```bash
terraform -chdir=terraform init
```

Review the planned infrastructure changes:

```bash
terraform -chdir=terraform plan
```

Apply the Terraform configuration:

```bash
terraform -chdir=terraform apply
```

> [!IMPORTANT]
> Terraform will automatically configure your GitHub repository with the necessary secrets and variables for the GitHub Actions workflow.

#### 3. Verify GitHub Configuration

After Terraform completes, verify that your GitHub repository has been configured with:

**Secrets** (in Settings → Secrets and variables → Actions → Secrets):
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`

**Variables** (in Settings → Secrets and variables → Actions → Variables):
- `GOOGLE_GENAI_USE_VERTEXAI`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `GOOGLE_CLOUD_STORAGE_BUCKET`
- `GCS_DIR_NAME`
- `AGENT_NAME`
- `LOG_LEVEL`
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`
- And other optional variables if configured

#### 4. Deploy Your First Agent

The GitHub Actions workflow (`.github/workflows/deploy-to-agent-engine.yaml`) will automatically trigger on:
- Pushes to the `main` branch
- Changes to `src/**`, `terraform/**`, or `uv.lock`

You can also manually trigger the workflow from the GitHub Actions tab.

To run the pipeline:

Navigate to your GitHub repository in your web browser, go to the "Actions" tab, and click "Run workflow" on the right side.

*-OR-*

Make a small change and push to main
```bash
touch test.txt
git add .
git commit -m "test: trigger CI/CD pipeline"
git push origin main
```

Monitor the workflow in your GitHub repository under the "Actions" tab.

> [!WARNING]
> **After your first deployment succeeds, complete Phase 2 to enable agent updates.**
>
> The initial deployment creates a new Agent Engine instance with a unique ID. You must record this ID in your environment to:
> - Update the deployed agent (instead of creating new instances)
> - Register the agent with Agentspace (optional)
>
> **Without completing Phase 2, every deployment will create a new Agent Engine instance instead of updating the existing one.**

### Phase 2: Enable Agent Engine Updates

After your first deployment succeeds, add the deployed Agent Engine ID to the `AGENT_ENGINE_ID` variable in your configuration to enable updates to that instance. **The deployment script ALWAYS creates a new instance when the `AGENT_ENGINE_ID` variable is not set.**

1. **Locate the Agent Engine ID** in your deployment logs:
   - Go to GitHub Actions → Your workflow run → "deploy-agent" step
   - Look for output like: `projects/PROJECT_ID/locations/LOCATION/reasoningEngines/1234567890123456789`
   - The Agent Engine ID is the final numeric component: `1234567890123456789`

2. **Update your local `.env` file** with the Agent Engine ID:
   ```bash
   AGENT_ENGINE_ID="1234567890123456789"  # replace with your actual ID

   # Optional: Customize display name and description
   AGENT_DISPLAY_NAME="My Production Agent"
   AGENT_DESCRIPTION="Customer service agent for product inquiries"

   # Optional: Enable Agentspace registration (requires an existing Agentspace app)
   AGENTSPACE_APP_ID="your-agentspace-app-id"
   AGENTSPACE_APP_LOCATION="global"  # or "us" or "eu"
   ```

3. **Sync configuration to GitHub** by running Terraform again:
   ```bash
   terraform -chdir=terraform apply
   ```

   This updates the GitHub Actions variables with your new `AGENT_ENGINE_ID` and any optional settings.

4. **Verify the configuration**:
   - Go to GitHub repository Settings → Secrets and variables → Actions → Variables
   - Confirm `AGENT_ENGINE_ID` is now set with your instance ID

**✅ Updates enabled!** Future deployments will now update your existing agent instance instead of creating new ones.

### Phase 3: Ongoing Development

Once you've completed the initial setup and update configuration, your steady-state development workflow becomes:

1. **Develop locally**: Modify agent app code and prompts
2. **Test locally**: Run `uv run local-agent` to verify changes
3. **Create PR**: Push to feature branch and open pull request
4. **Merge to main**: GitHub Actions automatically deploys on merge
5. **Verify deployment**: Test with `uv run remote-agent`

**Environment Updates**: If you need to change configuration (display name, Agentspace settings, etc.), update `.env` and run `terraform -chdir=terraform apply` to sync changes to GitHub variables.

> [!NOTE]
> **When to Use Terraform**
>
> You typically won't need Terraform during ongoing development, except for:
>
> - **Configuration changes**: Updating display name, Agentspace settings, or other environment variables
> - **IAM policy updates**: Modifying service account roles if agent requirements change
> - **API management**: Adding new Google Cloud APIs if needed by your agent
> - **Infrastructure cleanup**: Running `terraform destroy` to remove all resources
> - **Repository migration**: Connecting to a different GitHub repository

## Pipeline Stages

The CI/CD pipeline defined in the [GitHub workflow](../.github/workflows/deploy-to-agent-engine.yaml) consists of the following stages:

1. **Install Dependencies** - Installs project dependencies using `uv`
2. **Build a Wheel** - Builds a wheel file from the source code
3. **Deploy to Agent Engine** - Creates/updates the Vertex AI Agent Engine instance
4. **Register with Agentspace** - (Optional) Registers the Agent Engine instance with Agentspace

## Monitoring

### GitHub Actions Logs

Monitor deployment progress in your GitHub repository:
1. Go to the "Actions" tab
2. Click on the latest workflow run
3. Expand the steps to view detailed logs

### Google Cloud Logs

View agent logs in Google Cloud Console:
1. Navigate to Cloud Logging
2. Filter by resource:
```
resource.type="aiplatform.googleapis.com/ReasoningEngine"
resource.labels.reasoning_engine_id="1234567890123456789"  # replace with your deployed Agent Engine instance ID

```

## Infrastructure Components

### Service Accounts

Terraform creates two service accounts:

1. **CI/CD Service Account** (`{AGENT_NAME}-cicd`): Used by GitHub Actions for deployment
2. **App Service Account** (`{AGENT_NAME}-app`): Used by the deployed agent

View IAM role assignments in [`iam.tf`](../terraform/iam.tf)

### Workload Identity Federation

- Creates a Workload Identity Pool for GitHub Actions
- Allows GitHub Actions to authenticate to Google Cloud without storing service account keys
- Provider is configured to trust your specific GitHub repository

### Authentication Architecture

> [!IMPORTANT]
> **Why Service Account Impersonation is Required**
>
> This repository uses **Workload Identity Federation with service account impersonation** rather than direct workload identity. This is a hard requirement, not a design choice.
>
> **Technical reason**: The Agentspace registration script calls the Discovery Engine REST API, which requires OAuth2.0 access tokens. The Google GitHub Actions auth action only provides `access_token` outputs when using service account impersonation (via the `service_account` parameter). [Direct workload identity authentication](https://github.com/google-github-actions/auth?tab=readme-ov-file#preferred-direct-workload-identity-federation) does not expose access tokens.
>
> See the `setup_environment()` function in `src/{package_name}/deployment/register_agent.py` for the OAuth2.0 token usage.

### Enabled APIs

Terraform automatically enables these additional required services outside of those [enabled by default](https://cloud.google.com/service-usage/docs/enabled-service#default) in every new project:

| API Title | Service Name | Purpose |
|-----------|--------------|---------|
| Vertex AI API | `aiplatform.googleapis.com` | Agent deployment and management |
| Cloud Resource Manager API | `cloudresourcemanager.googleapis.com` | Manage project resources |
| Discovery Engine API | `discoveryengine.googleapis.com` | Agentspace registration |
| Cloud IAM API | `iam.googleapis.com` | Manage service accounts and IAM roles |
| IAM Service Account Credentials API | `iamcredentials.googleapis.com` | Generate OAuth2.0 tokens via service account impersonation |
| Security Token Service API | `sts.googleapis.com` | Exchange external credentials for Google Cloud access tokens (Workload Identity Federation) |
| Telemetry (OTLP) API | `telemetry.googleapis.com` | Collect OTLP trace data |

### Local State Management
This Terraform configuration uses **local state** (stored in `terraform.tfstate`) for simplicity and one-time setup. The state file is excluded from version control by the project root `.gitignore` file.

## Environment Variables Reference

**📖 [Complete Environment Variables Reference](environment_variables.md)** - See the comprehensive guide for all configuration options and detailed descriptions

**Quick reference for CI/CD setup:**
- Required: `AGENT_NAME`, `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_CLOUD_STORAGE_BUCKET`, `GITHUB_REPO_NAME`, `GITHUB_REPO_OWNER`
- Critical: `AGENT_ENGINE_ID` (set after first deployment to enable updates)
- Optional: See [complete guide](environment_variables.md) for all optional settings

## Cleanup

To remove all Terraform-managed resources:

```bash
cd terraform
terraform destroy
```

**Note**: This will remove the service accounts, IAM bindings, and GitHub repository configuration, but will not delete deployed Agent Engine instances or disable any APIs.

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**: Ensure your `gcloud` CLI authenticated Google Cloud user account has sufficient IAM roles
2. **GitHub API Errors**: Verify the GitHub repository name and owner in `.env` and ensure you're authenticated in the `gh` CLI with an admin account
3. **Terraform State Issues**: If state becomes corrupted, you may need to [refactor it](https://developer.hashicorp.com/terraform/language/state/refactor)

### Getting Help

- Check Terraform output for detailed error messages
- Review GitHub Actions logs for deployment failures
- Double-check environment variables set in `.env` mach those set in [GitHub Actions variables](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables)
- Review Google Cloud Logging Reasoning Engine resource logs

## Resources

- [Vertex AI | Agent Engine | Deploy an Agent](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy)

**[← Back to Documentation](../README.md#documentation)**
