# Customizing Your Agent

This repository is a **single-agent template** for deploying observable AI agents to Vertex AI Agent Engine. [Create a new repository from this template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template), customize the agent implementation in `src/agent_engine_cicd_base/`, and deploy with built-in CI/CD automation.

## Repository Structure

```
agent-engine-cicd-base/
├── .github/                          # GitHub Actions workflows
├── docs/                             # Setup guides and documentation
├── src/
│   └── agent_engine_cicd_base/       # Main package (rename when creating from template)
│       ├── agent.py                  # Agent implementation (customize this)
│       ├── callbacks.py              # Lifecycle callbacks for logging
│       ├── prompt.py                 # Agent instructions (customize this)
│       ├── tools.py                  # Custom tools (customize this)
│       ├── server.py                 # Local development server
│       ├── utils/                    # Observability and shared utilities
│       └── deployment/               # Deployment scripts (excluded from wheel)
├── terraform/                        # Infrastructure as Code for CI/CD
├── .env.example                      # Example environment variables
└── pyproject.toml                    # Dependencies and build config
```

**What to customize:**
- `src/agent_engine_cicd_base/agent.py` - Agent definition and configuration
- `src/agent_engine_cicd_base/prompt.py` - Agent instructions
- `src/agent_engine_cicd_base/tools.py` - Custom tool implementations
- `src/agent_engine_cicd_base/callbacks.py` - Optional callback customization
- `.env` - Environment configuration
- `pyproject.toml` - Manage project dependencies using `uv`

**What to keep:**
- `src/agent_engine_cicd_base/deployment/` - Deployment scripts (excluded from wheel)
- `src/agent_engine_cicd_base/utils/` - Standard observability setup
- `.github/` - CI/CD workflows
- `terraform/` - Infrastructure provisioning

**What to rename when creating from template:**
- Directory: `src/agent_engine_cicd_base/` → `src/your_package_name/`
- `pyproject.toml`: Update `name` and all `project.scripts` entry points
- `tests/`: Update imports from `agent_engine_cicd_base.*` to `your_package_name.*`
- Run `uv sync` to regenerate environment


## Customization Guide

### Step 1: Get the Template

```bash
# Create a new repository from this template on GitHub:
# Click "Use this template" → "Create a new repository"
# Then clone your new repository:
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO

# Copy environment template
cp .env.example .env
# Edit .env with your values (AGENT_NAME, GOOGLE_CLOUD_PROJECT, etc.)
```

See [GitHub's template documentation](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) for detailed instructions.

### Step 2: Customize Agent Implementation

**Main Agent Definition** (`src/agent_engine_cicd_base/agent.py`):
```python
root_agent = LlmAgent(
    name="your_agent_name",               # ← Change this
    description="Your agent description", # ← Change this
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"),
    instruction=return_instructions_root(),
    tools=[your_tool_1, your_tool_2],     # ← Add your tools
    # Callbacks can be customized in callbacks.py
)
```

**Agent Instructions** (`src/agent_engine_cicd_base/prompt.py`):
```python
def return_instructions_root() -> str:
    """Return agent instructions."""
    return """
    You are a helpful AI assistant that...    # ← Customize instructions
    """
```

**Custom Tools** (`src/agent_engine_cicd_base/tools.py`):
```python
def your_custom_tool(parameter: str) -> str:
    """Your custom tool implementation."""
    # Add your tool logic here
    return result
```

**Dependencies** (`pyproject.toml`):
```bash
# Add dependencies using uv
uv add your-package-name
```

### Step 3: Test and Deploy

**Local development:**
```bash
uv run local-agent  # Test at http://localhost:8000
```

**Deploy to production:**
- Set up CI/CD with the [GitHub Actions guide](cicd_setup_github_actions.md)
- Push to main branch for automated deployment

See the [Development Guide](development.md) for all commands and workflows.

## Environment Configuration

**📖 [Complete Environment Variables Reference](environment_variables.md)** - See the comprehensive guide for all configuration options

**Quick reference - Required variables** (`.env`):
```bash
AGENT_NAME="your-unique-agent-name"
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"
GOOGLE_CLOUD_STORAGE_BUCKET="your-staging-bucket"
GOOGLE_GENAI_USE_VERTEXAI="true"
```

**Common optional variables:**
- `LOG_LEVEL`, `ROOT_AGENT_MODEL`, `AGENT_DISPLAY_NAME`, `AGENT_DESCRIPTION`, `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`

## Best Practices

- **Start Simple**: Begin with the example weather/time agent and gradually customize
- **Test Locally**: Always test with `uv run local-agent` before deploying
- **Observe**: Monitor agent behavior via ADK web debugger, Google Cloud Trace, and Cloud Logging
- **Environment Variables**: Keep sensitive configuration in `.env` files (never commit)
- **Version Control**: Use feature branches and isolate prompt iterations
- **Documentation**: Document your agent's specific capabilities

## Resources

- [Google ADK | Quickstart](https://google.github.io/adk-docs/get-started/quickstart/)

**[← Back to Documentation](../README.md#documentation)**
