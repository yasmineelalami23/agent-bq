# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Removed

### Fixed

## [0.6.0] - 2025-11-18

### Added
- `TemplateConfig` Pydantic model for template initialization validation
- Auto-detection of repository name from git remote URL
- Global constants for template script reusability across projects
- Comprehensive unit tests for template validation
- Dual-output logging for template initialization (terminal + markdown file)
- Separate output files for dry-run and actual initialization runs

### Changed
- **BREAKING**: Flattened package structure by removing nested `agent/` subdirectory (moved agent.py, callbacks.py, prompt.py, tools.py up one level)
- Refactored template initialization with improved validation and error messages
- Template init script now saves execution logs to markdown files with timestamps
- Simplified summary output to use generic descriptions instead of hard-coded file lists
- Improved agent directory discovery in server.py with file-based path resolution (using `.resolve()` for absolute paths and symlink resolution) and environment variable override

### Removed
- `src/agent_engine_cicd_base/agent/__init__.py` (package structure simplified)

### Fixed
- Static date bug in global_instruction - now updates dynamically per request ([#76](https://github.com/onix-net/agent-engine-cicd-base/pull/76))

## [0.5.0] - 2025-11-14

### Added
- Template initialization script (`uv run init-template`) for automated repository setup
- `server.py` module for local development server (replaces `run_local_agent.py`)
- `server` console script alias for `local-agent` command
- Comprehensive changelog with retroactive version history ([#64](https://github.com/onix-net/agent-engine-cicd-base/pull/64))
- Semantic version tags for all major releases (v0.0.1 through v0.4.0)

### Changed
- **BREAKING**: Restructured to proper Python package layout
  - Moved `src/agent/` → `src/agent_engine_cicd_base/agent/`
  - Moved `src/scripts/` → `src/agent_engine_cicd_base/deployment/`
  - Updated all imports, entry points, and documentation
- Excluded `deployment/` directory from wheel package (tooling-only code)
- Made all documentation package-agnostic using `{package_name}` placeholders
- Simplified repository structure tree in customization guide
- Consolidated OpenTelemetry setup into single `setup_opentelemetry()` function ([#65](https://github.com/onix-net/agent-engine-cicd-base/pull/65))
- Replaced custom exporter with upstream `CloudLoggingExporter`
- Added process-level `SERVICE_INSTANCE_ID` tracking using process ID

### Removed
- `src/scripts/run_local_agent.py` (replaced by `src/agent_engine_cicd_base/server.py`)

### Documentation
- Updated all path references from old structure to new package layout
- Added initialization workflow to README.md and CLAUDE.md
- Clarified template usage with step-by-step renaming instructions

## [0.4.0] - 2025-10-23

### Added
- Pydantic models for type-safe environment configuration ([#57](https://github.com/onix-net/agent-engine-cicd-base/pull/57))
- `initialize_environment()` factory function eliminating boilerplate
- Comprehensive unit tests with 100% coverage requirement for config module
- Reusable pytest fixtures in `conftest.py` to eliminate individual test patching
- `@field_validator` for GitHub Actions empty string handling
- 53 unit tests with pytest, pytest-cov, and pytest-mock

### Changed
- Renamed `src/deployment/` to `src/scripts/` for better semantic clarity
- Removed deprecated `--dev` flag from `uv run` commands
- Standardized Terraform commands to use `-chdir=terraform` syntax
- Updated all imports and pyproject.toml entry points
- Simplified GitHub Actions deploy workflow Python setup
- Bumped GitHub Actions versions (checkout@v5, setup-uv@v6, setup-python@v6, paths-filter@v3)

### Fixed
- Added `AGENT_NAME` environment variable to registration workflow step ([#61](https://github.com/onix-net/agent-engine-cicd-base/pull/61))
- Fixed deployed agent name retrieval for delete prompt ([#56](https://github.com/onix-net/agent-engine-cicd-base/pull/56))

### Documentation
- Added `AGENT_ENGINE_ID` example to `.env.example`
- Added Terraform migration research and planning documentation ([#55](https://github.com/onix-net/agent-engine-cicd-base/pull/55))
- Clarified `AGENT_ENGINE_ID` extraction with explicit examples

## [0.3.0] - 2025-09-29

### Added
- Google GenAI instrumentation for improved observability ([#41](https://github.com/onix-net/agent-engine-cicd-base/pull/41))
- Custom exporter to fix nested bytes in Gemini responses
- Environment variables reference guide with all 18 configuration options ([#45](https://github.com/onix-net/agent-engine-cicd-base/pull/45))
- Comprehensive documentation reorganization with user journey TOC ([#43](https://github.com/onix-net/agent-engine-cicd-base/pull/43))
- Development guide (`docs/development.md`) with all dev commands and workflows

### Changed
- Replaced `google-generativeai` with `google-genai` instrumentor
- Consolidated OpenTelemetry setup into single `setup_opentelemetry()` function
- Streamlined README from ~200 to ~115 lines for first-time users
- Removed repository structure diagram from README (moved to customizing guide)
- Deleted redundant `docs/advanced_features.md`

### Fixed
- Clarified repository fork requirement for CI/CD setup ([#42](https://github.com/onix-net/agent-engine-cicd-base/pull/42))
- Added Phase 2 documentation for capturing `AGENT_ENGINE_ID` after first deployment

### Documentation
- Restructured CI/CD guide into three distinct phases
- Added comprehensive environment variables reference organized by category
- Clarified `AGENT_NAME` hyphen-to-underscore transformation
- Improved `.env.example` with clearer comments and missing variables

## [0.2.0] - 2025-09-25

### Added
- Comprehensive Terraform CI/CD infrastructure ([#36](https://github.com/onix-net/agent-engine-cicd-base/pull/36))
- Service accounts for CI/CD and app deployment with IAM roles
- Workload Identity Federation for GitHub Actions authentication
- GitHub Actions workflow for automated agent deployment
- Agentspace registration with federated authentication support ([#40](https://github.com/onix-net/agent-engine-cicd-base/pull/40))
- `safe_getenv()` helper to handle GitHub Actions empty string variables
- Real-time output in GitHub Actions with `PYTHONUNBUFFERED=1`
- Comprehensive Terraform + GitHub Actions documentation

### Changed
- Standardized environment variables with `AGENT_NAME` as base identifier
- Updated `.env.example` with streamlined configuration format
- Removed `OTEL_RESOURCE_ATTRIBUTES` configuration for simplicity
- Updated observability setup to use `AGENT_NAME` for service naming
- Sanitized agent names by replacing hyphens with underscores
- Migrated from multi-agent to single-agent template architecture ([#33](https://github.com/onix-net/agent-engine-cicd-base/pull/33))
- Modernized agent registration script with async support

### Fixed
- Corrected `uv build` flag from `--out_dir` to `--out-dir`
- Added federated authentication support for CI/CD environments
- Removed unused credential refresh import ([#39](https://github.com/onix-net/agent-engine-cicd-base/pull/39))
- Fixed deployment logging to use `api_resource.name`

### Documentation
- Created comprehensive GitHub Actions CI/CD setup guide
- Renamed Cloud Build docs to indicate deprecated status
- Streamlined deployment workflow guides ([#38](https://github.com/onix-net/agent-engine-cicd-base/pull/38))
- Added Agentspace registration documentation with streamlined workflow

## [0.1.0] - 2025-09-20

### Added
- OpenTelemetry instrumentation for production observability ([#29](https://github.com/onix-net/agent-engine-cicd-base/pull/29))
- Google Gen AI instrumentors for comprehensive LLM telemetry
- Cloud Logging integration with direct export using `CloudLoggingExporter`
- Always-on OTLP tracing with automatic export to Google Cloud Trace
- Automatic trace correlation in structured logging via `LoggingInstrumentor`
- Comprehensive OpenTelemetry documentation ([#32](https://github.com/onix-net/agent-engine-cicd-base/pull/32))
- Structured JSON logging with OpenTelemetry ([#27](https://github.com/onix-net/agent-engine-cicd-base/pull/27))
- Source location fields and proper UTC timezone for JSON logs
- Automatic staging bucket creation ([#23](https://github.com/onix-net/agent-engine-cicd-base/pull/23))
- Agent customization and management utilities ([#21](https://github.com/onix-net/agent-engine-cicd-base/pull/21))
- Conditional code quality automation ([#15](https://github.com/onix-net/agent-engine-cicd-base/pull/15))
- Automated Claude Code PR review workflow ([#14](https://github.com/onix-net/agent-engine-cicd-base/pull/14))
- Automated code quality checks with Ruff and MyPy ([#12](https://github.com/onix-net/agent-engine-cicd-base/pull/12))
- Observability configuration to CI/CD pipeline ([#30](https://github.com/onix-net/agent-engine-cicd-base/pull/30))

### Changed
- Migrated to single-agent template architecture ([#33](https://github.com/onix-net/agent-engine-cicd-base/pull/33))
- Streamlined documentation for better navigation ([#20](https://github.com/onix-net/agent-engine-cicd-base/pull/20))
- Split Claude workflow for automated reviews ([#19](https://github.com/onix-net/agent-engine-cicd-base/pull/19))
- Modernized OpenTelemetry setup and updated dependencies
- Required `GOOGLE_CLOUD_PROJECT` environment variable for trace export

### Fixed
- Celsius conversion in example agent ([#4](https://github.com/onix-net/agent-engine-cicd-base/pull/4))
- Empty assignments in `.env.example`
- Proper UTC timezone for JSON timestamps
- Handler clearing with console output ([#22](https://github.com/onix-net/agent-engine-cicd-base/pull/22))

### Documentation
- Completed README with comprehensive setup instructions ([#3](https://github.com/onix-net/agent-engine-cicd-base/pull/3))
- Fixed markdown formatting issues
- Added agent customization documentation
- Updated code quality automation documentation

## [0.0.1] - 2025-08-03

### Added
- Initial ADK agent deployment infrastructure ([#1](https://github.com/onix-net/agent-engine-cicd-base/pull/1))
- Google ADK integration for Vertex AI Agent Engine
- UV package manager configuration
- Python 3.12-3.13 support with Hatchling build system
- Core dependencies (google-adk, google-cloud-aiplatform)
- Environment configuration with python-dotenv
- GitHub Actions and Cloud Build initial configuration
- Initial project structure with `src/agent/` directory
- Example weather conversion agent
- Basic deployment scripts
- `.env.example` template
- Project documentation foundation

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- Implemented Application Default Credentials (ADC) for Google Cloud authentication

[Unreleased]: https://github.com/onix-net/agent-engine-cicd-base/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/onix-net/agent-engine-cicd-base/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/onix-net/agent-engine-cicd-base/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/onix-net/agent-engine-cicd-base/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/onix-net/agent-engine-cicd-base/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/onix-net/agent-engine-cicd-base/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/onix-net/agent-engine-cicd-base/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/onix-net/agent-engine-cicd-base/releases/tag/v0.0.1
