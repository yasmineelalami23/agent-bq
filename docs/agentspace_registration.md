# Agentspace Registration Guide

This guide covers registering deployed Agent Engine instances with Google Cloud Agentspace applications.

> [!IMPORTANT]
> The CI/CD pipeline will automatically register the Agent Engine instance after deployment when you set the `AGENTSPACE_APP_ID`, `AGENTSPACE_APP_LOCATION`, and `AGENT_ENGINE_ID` environment variables.
> You can manage registration manually using the scripts and commands described here.

## Overview

[**Agentspace**](https://cloud.google.com/agentspace/docs) is Google Cloud's search, AI assistant, and LLM agent platform that combines Google's search technology with generative AI. **Agent registration** connects your deployed Agent Engine instances to Agentspace applications, enabling users to interact with them in a Google-managed web experience from the [Agent Gallery](https://cloud.google.com/agentspace/docs/agents-gallery).

## Prerequisites

1. **Deploy Agent Engine Instance**: Complete agent deployment first using the [CI/CD setup guide](cicd_setup_github_actions.md) (or create the app service account and IAM roles manually before using the [manual deployment commands](../README.md#manual-deployment))
2. **Create Agentspace Application**: Set up an [Agentspace application](https://cloud.google.com/agentspace/docs/create-app) in Google Cloud Console
3. **Configure Environment Variables**: Add the following to your `.env` file:

**📖 [Complete Environment Variables Reference](environment_variables.md)** - See the comprehensive guide for all configuration options

**Quick reference for Agentspace:**
```bash
# Required: Agentspace configuration
AGENTSPACE_APP_ID="your-agentspace-app-id"
AGENTSPACE_APP_LOCATION="global"  # Options: global, us, eu
AGENT_ENGINE_ID="1234567890123456789"

# Required: Standard GCP configuration
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"

# Optional: Agent display information and API configuration
AGENT_DISPLAY_NAME="Your Agent Display Name"
AGENT_DESCRIPTION="Description of your agent's capabilities"
API_VERSION="v1alpha"
```

## Registration Workflow

### 1. Test Configuration
Verify your environment setup:
```bash
uv run test-register
```

### 2. Register Agent
Register with your Agentspace application:
```bash
uv run register
```
This automatically prevents duplicate registrations and confirms the result.

### 3. Verify Registration
List all registered agents:
```bash
uv run list-agents
```

## Management Commands

| Command | Purpose |
|---------|---------|
| `uv run register` | Register agent with Agentspace (prevents duplicates) |
| `uv run list-agents` | Show all registered agents with IDs and details |
| `uv run unregister` | Remove agent registration (requires confirmation) |
| `uv run test-register` | Validate environment configuration |

## Configuration Details

### Authentication
- **Local Development**: Uses Application Default Credentials (`gcloud auth application-default login`)
- **CI/CD**: Uses `GCP_ACCESS_TOKEN` from GitHub workflow (automatically provided)

### Region Configuration
The `AGENTSPACE_APP_LOCATION` determines the API endpoint:
- `global`: `discoveryengine.googleapis.com`
- `us`: `us-discoveryengine.googleapis.com`
- `eu`: `eu-discoveryengine.googleapis.com`

## Troubleshooting

### Common Issues

| Error | Solution |
|-------|----------|
| Missing required environment variable | Set required variables in `.env` |
| Error getting Application Default Credentials | Run `gcloud auth application-default login` |
| Agent already registered | Expected behavior (duplicates prevented automatically) |
| Agent Engine ID not registered | Verify `AGENT_ENGINE_ID` using `uv run list-agents` |
| HTTP 403 | Check IAM roles for Agentspace |
| Connection timeout | Retry after verifying connectivity |

### Debug Commands

```bash
# Test environment configuration
uv run test-register

# Check authentication
gcloud auth application-default print-access-token

# List current registrations
uv run list-agents

# Test deployed agent
uv run remote-agent
```

## Complete Example Workflow

```bash
# 1. Deploy agent (requires CI/CD setup or create the app service account and IAM roles manually)
uv run deploy

# 2. Configure .env with Agentspace variables
AGENTSPACE_APP_ID="your-app-id"
AGENTSPACE_APP_LOCATION="global"
AGENT_ENGINE_ID="1234567890123456789"

# 3. Register and verify
uv run test-register
uv run register
uv run list-agents

# 4. Test and cleanup
uv run remote-agent
uv run unregister    # Remove from Agentspace
uv run delete        # Delete Agent Engine instance
```

## Resources

- [Agentspace Overview](https://cloud.google.com/agentspace/docs)
- [Agentspace API Reference](https://cloud.google.com/agentspace/docs/reference/rest)
- [Agent Engine Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview)
- [Agent Engine Migration Guide](https://cloud.google.com/vertex-ai/generative-ai/docs/deprecations/agent-engine-migration)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Vertex AI Agent Builder](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-builder/overview)
- [Agentspace Console](https://console.cloud.google.com/gen-app-builder)

**[← Back to Documentation](../README.md#documentation)**
