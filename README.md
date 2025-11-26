# agent-engine-cicd-base
Base repo for deploying ADK apps to Agent Engine

## Overview

A **[Google ADK](https://google.github.io/adk-docs/) template repository** for deploying [observable AI agents](https://cloud.google.com/stackdriver/docs/instrumentation/ai-agent-overview) to [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview) with CI/CD automation.

**To Setup CI/CD**: [Create a new repository from this template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) (requires admin access on your new repository).

### Key Features

- **OpenTelemetry Observability**: Production-ready telemetry with Google AI instrumentors
- **Comprehensive Logging**: OpenTelemetry logging with trace correlation  
- **CI/CD Integration**: Automated deployment via GitHub Actions Workflows
- **Rapid Development**: `uv` scripts for prototyping and deployment
- **Code Quality**: Ruff formatting/linting and MyPy type checking

## Quickstart

This guide walks you through setting up a complete CI/CD pipeline for deploying AI agents to Vertex AI Agent Engine. The process follows four steps: **setup → develop → provision → deploy**.

> [!NOTE]
> **Local development only?** If you want to test locally without CI/CD, see the **[Development Guide](docs/development.md)** for clone-and-run instructions.

### Prerequisites
- Python 3.12 or 3.13
- [UV package and project manager](https://docs.astral.sh/uv/)
- [Google Cloud CLI](https://cloud.google.com/sdk/gcloud) configured with appropriate permissions
- [Terraform](https://www.terraform.io/) for infrastructure setup

### 1. Setup

**Get Code:**

Create a new repository from this template (required for CI/CD automation):

```sh
# Use this template on GitHub: Click "Use this template" → "Create a new repository"
# Then clone your new repository:
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO
```

See [GitHub's template documentation](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) for detailed instructions.

**Install UV:**
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# See https://docs.astral.sh/uv/ for Windows and other options
```

**Initialize from template:**
```sh
uv run init-template
# Prompts for package name and GitHub details, then automatically:
# - Renames package directories
# - Updates configuration files
# - Resets CHANGELOG
# - Regenerates lockfile
```

**Configure environment variables:**
```sh
cp .env.example .env
# Edit .env with your values
```

**Required variables for CI/CD:**
- `AGENT_NAME` - Unique agent identifier
- `GOOGLE_CLOUD_PROJECT` - Your GCP project ID
- `GOOGLE_CLOUD_LOCATION` - Vertex AI region (e.g., us-central1)
- `GOOGLE_CLOUD_STORAGE_BUCKET` - Staging bucket for deployment
- `GOOGLE_GENAI_USE_VERTEXAI=true` - Enable Vertex AI
- `GITHUB_REPO_NAME` - Your repository name
- `GITHUB_REPO_OWNER` - Your GitHub username or organization

See **[Environment Variables Reference](docs/environment_variables.md)** for all configuration options.

### 2. Develop / Prototype

Test your agent locally before deploying:

```sh
uv run local-agent
```

Open `http://localhost:8000` in your browser and select `agent` to interact with your agent.

See the **[Development Guide](docs/development.md)** for additional testing options and commands.

### 3. Provision Infrastructure

**Initialize and apply Terraform configuration:**

```sh
# Initialize Terraform
terraform -chdir=terraform init

# Provision infrastructure
terraform -chdir=terraform apply
```

This will:
- Provision required GCP infrastructure (service accounts, APIs, storage)
- Configure GitHub repository secrets and variables for CI/CD

For complete CI/CD setup details, see **[CI/CD Setup (GitHub Actions)](docs/cicd_setup_github_actions.md)**.

### 4. Trigger Deployment

Create a feature branch, commit your changes, push to GitHub and open a pull request:

```sh
git checkout -b feat/initial-agent-setup
git add .
git commit -m "feat: initial agent setup"
git push origin feat/initial-agent-setup
```

Open a pull request to merge into `main`. Once merged, GitHub Actions will automatically:
- Build your agent package
- Deploy to Vertex AI Agent Engine
- Output the Agent Engine Resource name in the workflow logs

> [!IMPORTANT]
> After first deployment, capture the `AGENT_ENGINE_ID` from the Agent Engine Resource name in GitHub Actions logs, add it to your `.env` file, and run `terraform -chdir=terraform apply` again to sync it to GitHub variables. This enables agent updates instead of creating new instances on each deployment.
>
> **Example**: for Agent Engine Resource name `projects/PROJECT_ID/locations/LOCATION/reasoningEngines/1234567890123456789` -> `AGENT_ENGINE_ID="1234567890123456789"`

## Documentation

### Getting Started
- **[Development Guide](docs/development.md)** - Commands, workflows, and testing
- **[Environment Variables Reference](docs/environment_variables.md)** - Complete configuration guide
- **[Customizing Your Agent](docs/customizing_agent.md)** - Implementation details and architecture

### Deployment
- **[CI/CD Setup (GitHub Actions)](docs/cicd_setup_github_actions.md)** - Automated deployment with GitHub Actions
- **[CI/CD Setup (Cloud Build)](docs/cicd_setup_google_cloud_build.md)** - Alternate CI/CD using Cloud Build

### Production Features
- **[Agentspace Registration](docs/agentspace_registration.md)** - Connect agents to Agentspace apps
- **[Observability](docs/observability.md)** - OpenTelemetry instrumentation and monitoring
- **[Code Quality Automation](docs/code_quality_automation.md)** - Automated reviews and checks

### API Reference
- **[Discovery Engine API Operations](docs/discoveryengine_api_agent_operations.md)** - REST API reference for Agentspace
