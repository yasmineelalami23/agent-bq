# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **template repository** for deploying observable AI agents to Vertex AI Agent Engine. Users must **create a new repository from this template** to enable CI/CD automation (requires admin access to configure GitHub secrets/variables via Terraform).

### Two Usage Paths
1. **Quick Prototyping**: Clone directly → test locally (no CI/CD)
2. **Production Development**: Create from template → test locally → set up CI/CD → deploy

## Documentation Strategy

This repository follows a **streamlined documentation approach** with opinionated workflow guidance:
- **README.md**: Opinionated 4-step quickstart guide (setup → develop → provision → deploy) optimized for CI/CD setup with comprehensive documentation TOC organized by user journey (Getting Started, Deployment, Production Features, API Reference)
- **docs/development.md**: All development commands, local testing workflows, and manual deployment instructions (for clone-only usage without CI/CD)
- **docs/customizing_agent.md**: Repository structure and agent customization guide
- **docs/ directory**: Comprehensive guides for CI/CD, observability, and production features
- **CLAUDE.md**: Development commands and technical reference for Claude Code

### README Quickstart Flow
The README quickstart follows a **4-step opinionated workflow** focused on getting CI/CD operational quickly:
1. **Setup**: Create from template → install UV → configure `.env` with required CI/CD variables
2. **Develop/Prototype**: Test locally with `uv run local-agent` before deploying
3. **Provision Infrastructure**: Run Terraform commands (`init`, `plan`, `apply`) from repo root to provision GCP infrastructure and configure GitHub secrets/variables
4. **Trigger Deployment**: Create feature branch → commit → push → open PR → merge to main to trigger GitHub Actions deployment

**Key principle**: The README focuses on the CI/CD path. Users wanting local-only development are directed to the Development Guide.

### CI/CD Setup Documentation Structure
The CI/CD guide (`docs/cicd_setup_github_actions.md`) is organized into three distinct phases:
1. **Phase 1: Initial Terraform Setup** - Provision infrastructure (Terraform does NOT deploy the agent)
2. **Phase 2: Enable Agent Engine Updates** - After first GitHub Actions deployment, capture `AGENT_ENGINE_ID` from workflow logs, update `.env`, run `terraform apply` to sync to GitHub variables (enables updates instead of creating new instances)
3. **Phase 3: Ongoing Development** - Feature branch workflow with PR-based deployments to main

**Critical requirement**: After the first deployment via GitHub Actions, users must complete Phase 2 to enable updates. Without setting `AGENT_ENGINE_ID`, every deployment creates a new Agent Engine instance instead of updating the existing one.

## Development Commands

### Environment Setup
```bash
# Initialize from template (first-time setup only)
uv run init-template
# Auto-detects repository name from git, validates kebab-case naming,
# derives snake_case package name, and updates all files automatically.
# Enforces proper Python package naming conventions from the start.

# Install dependencies (including dev group)
uv sync --all-extras

# Copy environment template and configure
cp .env.example .env
# Edit .env with actual values for GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_GENAI_USE_VERTEXAI=true
```

### Local Development and Testing
```bash
# Recommended: Run agent using local script with full observability and Cloud Trace export
uv run local-agent

# Alternative: Run agent in the native ADK web UI for basic observability (specify parent directory)
uv run adk web src

# Run agent in terminal (specify agent directory)
uv run adk run src/agent

# Add dependencies
uv add package-name          # Runtime dependency
uv add package-name --dev    # Development dependency

# Update all dependencies
uv lock --upgrade
```

### Code Quality and Testing

**Automated AI Reviews**: Claude Code automatically reviews all PRs and responds to `@claude` comments.

**Automated Quality Checks**: Ruff formatting/linting and MyPy type checking run on all PRs using a conditional workflow strategy that only runs when relevant files change, saving CI resources.

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type checking
uv run mypy

# Run all checks at once (recommended before creating PRs)
uv run ruff format && uv run ruff check && uv run mypy

# Run unit tests
uv run pytest

# Run unit tests with coverage (100% required for config module)
uv run pytest --cov
```

**Important**: Always run these commands locally before creating pull requests to ensure automated checks pass.

### Changelog and Versioning Workflow

This project maintains a comprehensive changelog following [Keep a Changelog](https://keepachangelog.com/) format with semantic versioning.

**Required for Every PR:**
- **ALWAYS** add an entry to the `[Unreleased]` section of `CHANGELOG.md`
- Categorize changes appropriately:
  - `Added` - New features
  - `Changed` - Changes to existing functionality
  - `Deprecated` - Soon-to-be removed features
  - `Removed` - Removed features
  - `Fixed` - Bug fixes
  - `Security` - Security-related changes
- Include PR number references: `([#123](https://github.com/{owner}/{repository}/pull/123))`
- Keep entries concise and user-focused (what changed, not implementation details)
- **Do NOT include changes to `CLAUDE.md`** (internal documentation only)

**Release Process (User-Initiated):**
When the user decides accumulated changes warrant a release:
1. User indicates readiness to cut a release
2. Use `git-guru` agent to:
   - Review `[Unreleased]` section
   - Determine appropriate semantic version (MAJOR.MINOR.PATCH)
   - Move Unreleased entries to new versioned section with date
   - Create annotated git tag
   - Push tag to remote
3. User can then create a GitHub release from the tag

**Version Strategy:**
- Use **0.x.x** versioning (appropriate for template repository)
- Follow semantic versioning principles:
  - **MAJOR** (0.x.0): Breaking changes, major architectural shifts
  - **MINOR** (0.x.0): New features, significant enhancements
  - **PATCH** (0.0.x): Bug fixes, documentation updates, minor improvements

**Example Unreleased Entry:**
```markdown
## [Unreleased]

### Added
- New feature for X with Y capability ([#123](https://github.com/{owner}/{repository}/pull/123))

### Fixed
- Corrected Z behavior in edge case ([#124](https://github.com/{owner}/{repository}/pull/124))
```

### Setup CI/CD with Terraform

The Terraform configuration sets its variable values by reading the local `.env` file (created by copying .env.example and adding project-specific values).

```bash
# Initialize Terraform (run from repo root)
terraform -chdir=terraform init

# Preview infrastructure changes
terraform -chdir=terraform plan

# Provision infrastructure and configure GitHub secrets/variables
terraform -chdir=terraform apply
```

### Deployment

**⚠️ Recommended Workflow**: Complete [Terraform + GitHub Actions setup](docs/cicd_setup_github_actions.md) first to configure required service accounts and APIs, then use CI/CD for deployments.

**Manual Deployment** (requires CI/CD infrastructure setup):
```bash
# Build wheel package
uv build --wheel --out-dir .

# Deploy to Agent Engine
uv run deploy

# Test deployed agent
uv run remote-agent

# Agentspace Registration (optional)
uv run register               # Register agent with Agentspace app
uv run list-agents            # List all agents registered with the Agentspace app
uv run unregister             # Unregister agent from Agentspace (requires confirmation)

# Test deployment and registration scripts environment setup
uv run test-deploy            # Test deployment environment setup
uv run test-register          # Test registration environment setup

# Cleanup commands
uv run delete                 # Delete Agent Engine instance (requires AGENT_ENGINE_ID)
```

**Note**: Manual deployment requires service accounts and APIs to be configured. See the [CI/CD setup guide](docs/cicd_setup_github_actions.md) for infrastructure prerequisites.

## Architecture

This is a **Google ADK (Agent Development Kit) application** for deploying AI agents to Vertex AI Agent Engine. The repository uses a **modular architecture** that separates agent-specific logic from shared script infrastructure.

**📖 [Complete Architecture Guide](docs/customizing_agent.md)** - Detailed modular design, components breakdown, and deployment flow

### Quick Reference

- **Agent Implementation** (`src/{package_name}/agent/`): Self-contained agent implementation with standardized utilities
- **Deployment Infrastructure** (`src/{package_name}/deployment/`): Deployment scripts for Agent Engine (excluded from wheel)
- **Development Flow**: Local prototyping → CI/CD → Production deployment
- **Customizing Your Agent**: Modify `src/{package_name}/agent/` directory with your implementation

## Script Configuration Architecture

The scripts use **Pydantic models for type-safe environment configuration** with a simple factory function that handles validation and error handling. This modern Python pattern provides better validation, encapsulation, and developer experience.

### Configuration Models (`src/{package_name}/deployment/config.py`)

**Model Hierarchy:**
- `BaseEnv`: Shared fields (PROJECT, LOCATION, AGENT_NAME) with computed `service_account` property
- `DeployEnv(BaseEnv)`: Deploy/update operations with optional `agent_engine_id`
- `DeleteEnv(BaseEnv)`: Delete operations (requires `agent_engine_id`)
- `RegisterEnv(BaseEnv)`: Agentspace registration with computed `reasoning_engine` and `endpoint` properties
- `RunRemoteEnv(BaseEnv)`: Remote agent testing requirements
- `RunLocalEnv`: Minimal local development config (PROJECT only)
- `TemplateConfig`: Template initialization with kebab-case validation and computed `package_name` property

**Factory Function:**
- `initialize_environment(model_class, override_dotenv=True, print_config=True)`: Loads `.env`, validates environment, prints config, and returns typed model instance

**Key Features:**
- **DRY initialization**: Single factory function eliminates boilerplate across all scripts
- **On-demand validation**: Each function validates only required variables
- **Empty string handling**: `@field_validator` converts empty strings → None (GitHub Actions compatibility)
- **Computed properties**: Derived values like `service_account`, `reasoning_engine`, `endpoint` calculated automatically
- **Type safety**: Full mypy support with IDE autocomplete
- **Clear error messages**: Pydantic shows exactly what's missing/invalid with actual env var names
- **Consistent behavior**: Always exits on validation failure with proper exit codes

**Usage Pattern:**
```python
from .config import initialize_environment, DeployEnv

def deploy() -> None:
    # Load and validate environment configuration
    env = initialize_environment(DeployEnv)

    # Use typed, validated configuration
    client = vertexai.Client(
        project=env.google_cloud_project,
        location=env.google_cloud_location,
    )
```

**Benefits:**
- Eliminates 8 lines of boilerplate per function
- Each operation explicitly declares dependencies
- No global namespace pollution
- Easy to test with mock configurations
- Self-documenting with field descriptions
- Predictable exit codes for CI/CD automation

### Unit Tests (`tests/test_config.py`)

The config module has **comprehensive unit tests with 100% code coverage requirement**. Tests use reusable pytest fixtures from `tests/conftest.py` to eliminate individual test patching.

**Test Coverage:**
```bash
# Run tests with coverage report (100% required as configured in pyproject.toml)
uv run pytest --cov
```

Coverage configuration in `pyproject.toml` specifies:
- Include only `src/{package_name}/deployment/config.py`
- Fail if coverage drops below 100%
- Show missing lines in report

**Test Organization:**
- **Reusable Fixtures** (`tests/conftest.py`):
  - **Environment Data**: `valid_base_env`, `valid_deploy_env`, `valid_delete_env`, `valid_register_env`, `valid_remote_env`, `valid_local_env` - Pre-configured environment dictionaries for each model
  - **Test Isolation**: `clean_environment` - Auto-used fixture that removes environment variables before each test
  - **Mock Helpers**:
    - `mock_load_dotenv` - Auto-mocking for load_dotenv function
    - `mock_sys_exit` - Mock sys.exit with SystemExit side effect
    - `set_environment` - Helper to set multiple environment variables at once
    - `mock_print_config` - Context manager factory for mocking print_config on any model class
    - `mock_environ` - Mimics `os.environ` behavior for testing

**Test Classes:**
- `TestValidationBase`: Empty string filtering, GitHub Actions compatibility
- `TestBaseEnv`: Base model validation and computed properties
- `TestDeployEnv`: Deploy-specific validation and environment variable handling
- `TestDeleteEnv`: Delete operation requirements
- `TestRegisterEnv`: Agentspace registration with computed endpoints
- `TestRunRemoteEnv`: Remote agent testing configuration
- `TestRunLocalEnv`: Minimal local development requirements
- `TestTemplateConfig`: Template initialization kebab-case validation and snake_case derivation
- `TestInitializeEnvironment`: Factory function behavior with success/failure scenarios
- `TestEdgeCases`: GitHub Actions empty strings, unicode, edge cases

**Key Testing Patterns:**
- **DRY fixture pattern**: Eliminates ~50 lines of repetitive patching boilerplate across 800+ lines of tests
- **Fixture composition**: Combines multiple fixtures (e.g., `set_environment` + `mock_load_dotenv`) for complex test scenarios
- **Type-safe fixtures**: All fixtures use precise type hints (`Callable`, `Generator`, `AbstractContextManager`) for IDE support
- **Required/optional validation**: Tests validate both required and optional fields with defaults
- **GitHub Actions compatibility**: Empty string filtering tested (unset vars return `""`)
- **Computed properties**: `service_account`, `reasoning_engine`, `endpoint` verified
- **Error message validation**: Ensures errors show actual environment variable names (aliases)

## Template Initialization Script

The `init_template.py` script automates repository setup when creating from the template. It enforces Python package naming conventions and configures the repository automatically.

### Key Features

**Auto-Detection and Validation:**
- Detects repository name from `git remote get-url origin`
- Validates repository name follows kebab-case pattern: `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$`
- Auto-derives snake_case package name from kebab-case repository name
- Fails fast with clear instructions if naming doesn't conform

**Modular Design:**
- Global constants (`ORIGINAL_PACKAGE_NAME`, `ORIGINAL_REPO_NAME`) for reusability
- Single point of change when adapting for other template projects
- Pydantic validation via `TemplateConfig` model in `config.py`

**Operations Performed:**
1. Validates repository name (must be kebab-case)
2. Renames `src/{ORIGINAL_PACKAGE_NAME}/` to `src/{package_name}/`
3. Updates configuration files (pyproject.toml, test files, CLAUDE.md, README.md)
4. Replaces CHANGELOG.md with fresh template
5. Regenerates UV lockfile (`uv sync`)

### Usage

```bash
# Run initialization (auto-detects from git)
uv run init-template

# Dry-run mode (preview changes)
uv run init-template --dry-run
```

**Expected workflow:**
1. Create new repository from template on GitHub (use kebab-case name)
2. Clone locally: `git clone <repo-url>`
3. Run init script: `uv run init-template`
4. Script auto-detects `my-agent` → derives `my_agent` package name
5. Updates all files automatically

**Enforcement Philosophy:**
The script enforces Python naming conventions from the start by **requiring** kebab-case repository names. Invalid names (e.g., `MyNewRepo`, `my_agent`) trigger clear error messages instructing users to delete and recreate the repository with proper naming.

### Reusability

To adapt this script for another template project:

```python
# Update constants in init_template.py
ORIGINAL_PACKAGE_NAME = "my_template_pkg"
ORIGINAL_REPO_NAME = "my-template-repo"
```

All replacements, directory renaming, and user messages automatically adapt to the new values.

### Validation Model

**TemplateConfig (in config.py):**
```python
class TemplateConfig(BaseModel):
    repo_name: str = Field(
        ...,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
        description="GitHub repository name (kebab-case)",
    )

    @computed_field
    @property
    def package_name(self) -> str:
        """Python package name (kebab-case → snake_case)."""
        return self.repo_name.replace("-", "_")
```

**Comprehensive test coverage (11 tests):**
- Valid kebab-case names
- Invalid uppercase, underscore, special characters
- Boundary cases (hyphens at start/end, empty string)
- Package name derivation
- Computed field behavior

## Environment Variables

**📖 [Complete Environment Variables Reference](docs/environment_variables.md)** - Comprehensive guide to all configuration options

### Quick Reference

**Required for deployment:**
- `AGENT_NAME`: Unique agent identifier for resources and logs
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `GOOGLE_CLOUD_LOCATION`: Vertex AI region (e.g., us-central1)
- `GOOGLE_CLOUD_STORAGE_BUCKET`: Staging bucket for deployment
- `GOOGLE_GENAI_USE_VERTEXAI`: Must be "true" for deployment

**Required for CI/CD setup:**
- `GITHUB_REPO_NAME`: Repository name
- `GITHUB_REPO_OWNER`: GitHub username or organization

**Critical for updates and Agentspace:**
- `AGENT_ENGINE_ID`: Existing engine ID (enables updates instead of creating new instances)

**Development (Optional):**
- `AGENT_DIR`: Override agent directory discovery (defaults to `src/` relative to package root)

See the [complete guide](docs/environment_variables.md) for all optional configuration, observability settings, and detailed descriptions.

### Agent Directory Discovery

The local development server (`server.py`) discovers the agent directory using this logic:
1. **Environment Override**: If `AGENT_DIR` is set, use that path (absolute or relative)
2. **File-Based Fallback**: If `AGENT_DIR` is not set, use the package parent directory (one level above `server.py`)

**Default Behavior:**
- `AGENT_DIR` defaults to `src/` (the parent directory of the package)
- This works correctly whether running from the repository root or from any subdirectory
- The fallback is file-based rather than current-working-directory-based, making it more robust

**When to Override AGENT_DIR:**
- Running agents from a non-standard directory structure
- Testing multiple agent implementations without restructuring
- Development workflows with custom directory organization
- Debugging agent discovery issues

**Example Usage:**
```bash
# Run with custom agent directory
AGENT_DIR=/path/to/custom/agents uv run local-agent

# Or add to .env for persistent configuration
# AGENT_DIR="./custom-agents"
uv run local-agent
```

## Build Configuration

- **Python Version**: 3.12-3.13 required
- **Package Manager**: UV (modern Python package manager)
- **Code Quality**: Ruff for formatting/linting, MyPy for type checking
- **Build System**: Hatchling with wheel packaging
- **Core Dependencies**: 
  - google-adk
  - google-cloud-aiplatform[agent-engines]
  - OpenTelemetry instrumentation packages for observability
  - python-dotenv for environment management

## CI/CD Integration

**Recommended Approach**: Terraform + GitHub Actions (Three-phase setup)
- **Prerequisites**: Create a new repository from this template (requires admin access on your new repository)
- **Phase 1**: Run `terraform -chdir=terraform init/plan/apply` to provision infrastructure and configure GitHub repository secrets/variables (does NOT deploy agent)
- **Phase 2**: After first GitHub Actions deployment, capture `AGENT_ENGINE_ID` from workflow logs, update `.env`, run `terraform -chdir=terraform apply` again to enable updates
- **Phase 3**: Ongoing development with feature branch workflow → PR → merge to main triggers deployment
- **Pipeline**: GitHub Actions workflow automatically triggers on main branch merges using the `.github/workflows/deploy-to-agent-engine.yaml` file
- **Authentication**: Secure Workload Identity Federation (no stored keys) - uses service account impersonation as required by the GitHub Google Auth Action to generate an OAuth 2.0 `access_token` output, which is then required for the Agentspace registration script
- **Documentation**: `docs/cicd_setup_github_actions.md`

**Deprecated**: Manual Cloud Build Setup
- **Status**: Kept for reference only - not recommended for new projects
- **Documentation**: `docs/cicd_setup_google_cloud_build.md`

The GitHub Actions pipeline supports a 4-step deployment process:
1. **install-dependencies**: UV sync with frozen lockfile
2. **build-wheel**: Generate wheel package
3. **deploy-agent**: Deploy to Agent Engine (creates new instance if `AGENT_ENGINE_ID` not set, updates existing instance if set)
4. **register-agentspace**: Optional Agentspace registration (requires AGENTSPACE_APP_ID, AGENTSPACE_APP_LOCATION, and AGENT_ENGINE_ID)

## Logging Behavior

The repository uses **custom OpenTelemetry observability** consistently across all environments:

### Consistent Custom Implementation
- **Consolidated Setup**: Single `setup_opentelemetry()` function used for both local and deployed environments
- **Resource Configuration**: `configure_otel_resource()` helper sets `OTEL_RESOURCE_ATTRIBUTES` environment variable with service name and process-level instance ID
- **OpenTelemetry Integration**: All logs automatically exported to Google Cloud Logging using upstream `CloudLoggingExporter`
- **Trace Correlation**: Logs include trace context via `LoggingInstrumentor` for comprehensive observability
- **Process-Level Tracking**: Custom resource configuration with `SERVICE_INSTANCE_ID` based on process ID
- **TracerProvider Logic**: Detects and augments existing provider in local dev (ADK compatibility) or creates new provider in deployment
- **Environment Variables**:
  - `AGENT_NAME`: Unique service identifier (required)
  - `LOG_LEVEL`: Controls logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL) - defaults to INFO

### Environment Behavior
- **All Environments** (`uv run local-agent`, deployed agents):
  - Identical logging and tracing configuration
  - Logs exported to Google Cloud Logging with trace correlation
  - Traces exported to Google Cloud Trace via OTLP
  - Custom setup coexists with ADK's internal telemetry (enables ADK web UI traces in local development)
  - **Production Recommendation**: Set `LOG_LEVEL=INFO` to minimize logging costs

### Authentication
- Uses Application Default Credentials (ADC) for Google Cloud integration
- Requires `GOOGLE_CLOUD_PROJECT` environment variable for trace and log export

**📖 [Complete Observability Guide](docs/observability.md)** - OpenTelemetry instrumentation and monitoring details

## Observability Features

This repository includes custom OpenTelemetry instrumentation for production-ready observability.

### Implementation
- **Custom Setup**: Consolidated `setup_opentelemetry()` function used consistently across all environments
- **Always Enabled**: Observability is automatically configured for both local and deployed agents
- **Resource Configuration**: `configure_otel_resource()` helper sets `OTEL_RESOURCE_ATTRIBUTES` with service name and process-based instance ID
- **Google Gen AI Instrumentors**: Comprehensive LLM telemetry via `GoogleGenAiSdkInstrumentor`
- **Cloud Logging Integration**: Direct export to Google Cloud Logging using upstream `CloudLoggingExporter`
- **OTLP Tracing**: Export to Google Cloud Trace via authenticated OTLP endpoint
- **Trace Correlation**: Logging automatically includes trace context via `LoggingInstrumentor`
- **ADK Compatibility**: TracerProvider detection logic ensures custom setup coexists with ADK's internal telemetry without provider collisions

### What's Instrumented
- **LLM Calls**: Google Generative AI SDK operations automatically traced with semantic conventions
- **HTTP Requests**: External API calls automatically instrumented
- **Structured Logging**: JSON logs with trace correlation for Google Cloud Logging
- **Tool Invocations**: Agent tool calls include invocation context for debugging

### Configuration
- **Minimal Configuration**: Requires only `AGENT_NAME` and `GOOGLE_CLOUD_PROJECT` environment variables
- **Service Identification**: Custom resource with `SERVICE_INSTANCE_ID` based on process ID
- **Authentication**: Uses Application Default Credentials (ADC) for Google Cloud integration
- **Environment Variables**:
  - `AGENT_NAME`: Unique service identifier (required for resource configuration)
  - `GOOGLE_CLOUD_PROJECT`: Required for trace and log export
  - `LOG_LEVEL`: Optional logging verbosity (default: INFO)

### Usage
```bash
# Recommended: Local development with full observability (ADK web UI + Cloud observability)
uv run local-agent

# Production deployment (same observability configuration as local)
uv run deploy

# Test remote deployment with observability
uv run remote-agent
```

**Note**: The custom implementation provides consistent observability across local and deployed environments, with process-level service instance tracking. The setup is centralized in `src/{package_name}/utils/observability.py`.
