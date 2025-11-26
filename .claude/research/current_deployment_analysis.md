# Current Deployment Analysis: Python to Terraform Migration

**Date:** 2025-10-09
**Repository:** agent-engine-cicd-base
**Analysis Scope:** Understanding current Python-based Agent Engine deployment for Terraform migration

## Executive Summary

The current implementation uses a **hybrid approach**: Terraform provisions "setup once" infrastructure (service accounts, IAM, WIF, GitHub config), while Python scripts handle "deploy repeatedly" operations (Agent Engine instances, GCS bucket creation). This analysis documents what needs to migrate to Terraform for a fully infrastructure-as-code approach.

### Current State
- **Terraform:** CI/CD infrastructure (service accounts, WIF, GitHub secrets/variables, API enablement)
- **Python:** Agent Engine deployment, GCS bucket creation/validation, Agentspace registration
- **GitHub Actions:** Orchestrates Python deployment scripts

### Migration Goal
Move Agent Engine instance management and GCS bucket creation from Python to Terraform while maintaining the deployment workflow.

---

## 1. Complete Resource Inventory

### 1.1 Resources Currently Managed by Terraform

**Location:** `terraform/`

#### Google Cloud Resources

**Service Accounts** (`iam.tf`):
- `google_service_account.cicd` - CI/CD runner service account (`{AGENT_NAME}-cicd`)
- `google_service_account.app` - Application runtime service account (`{AGENT_NAME}-app`)

**IAM Roles** (`iam.tf`):
- **App Service Account Roles:**
  - `roles/aiplatform.user` - Vertex AI operations
  - `roles/logging.logWriter` - Cloud Logging
  - `roles/cloudtrace.agent` - Cloud Trace
  - `roles/telemetry.tracesWriter` - Telemetry
  - `roles/serviceusage.serviceUsageConsumer` - Service usage

- **CI/CD Service Account Roles:**
  - `roles/aiplatform.user` - Vertex AI operations
  - `roles/discoveryengine.editor` - Agentspace operations
  - `roles/iam.serviceAccountUser` - Service account impersonation
  - `roles/logging.logWriter` - Cloud Logging
  - `roles/storage.admin` - Full GCS access

**Workload Identity Federation** (`iam.tf`):
- `google_iam_workload_identity_pool.github` - Workload identity pool for GitHub Actions
- `google_iam_workload_identity_pool_provider.github` - OIDC provider for GitHub
- `google_service_account_iam_member.github_workload` - WIF binding to CI/CD service account

**API Enablement** (`services.tf`):
- `aiplatform.googleapis.com` - Vertex AI
- `cloudresourcemanager.googleapis.com` - Resource management
- `discoveryengine.googleapis.com` - Agentspace
- `iam.googleapis.com` - IAM
- `iamcredentials.googleapis.com` - OAuth token generation
- `sts.googleapis.com` - Security Token Service (WIF)
- `telemetry.googleapis.com` - OTLP traces

#### GitHub Resources

**Secrets** (`github.tf`):
- `GCP_WORKLOAD_IDENTITY_PROVIDER` - WIF provider name
- `GCP_SERVICE_ACCOUNT` - CI/CD service account email

**Variables** (`github.tf`):
Dynamically set from `.env` file - up to 13 variables:
- Required: `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_CLOUD_STORAGE_BUCKET`, `AGENT_NAME`
- Optional: `GCS_DIR_NAME`, `AGENT_DISPLAY_NAME`, `AGENT_DESCRIPTION`, `AGENT_ENGINE_ID`, `LOG_LEVEL`, `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`, `AGENTSPACE_APP_ID`, `AGENTSPACE_APP_LOCATION`

#### Configuration Management

**Data Sources:**
- `data.dotenv.adk` - Reads `.env` file for configuration
- Validates required keys exist and are non-empty
- Extracts GitHub variables from workflow keys

**State Management:**
- Local state (`terraform.tfstate`)
- Excluded from version control
- Single-environment setup (no remote backend)

### 1.2 Resources Currently Managed by Python Scripts

**Location:** `src/deployment/`

#### deploy_agent.py

**GCS Staging Bucket** (`confirm_or_create_bucket()` function, lines 98-153):
- **Creation:**
  - Checks if bucket exists via `bucket.reload()`
  - Creates bucket if missing (HTTP 404)
  - Sets uniform bucket-level access: `True`
  - Sets public access prevention: `enforced`
  - Creates in specified location or US multi-region (default)

- **Configuration:**
  - Bucket name: `GOOGLE_CLOUD_STORAGE_BUCKET` env var
  - Location: `GOOGLE_CLOUD_LOCATION` env var (optional, defaults to US)
  - Security: Uniform bucket-level access + public access prevention

- **Validation:**
  - Confirms bucket exists before Vertex AI initialization
  - Exits with error if creation fails
  - Handles conflicts (bucket already exists)
  - Handles permission errors (403 Forbidden)

**Agent Engine Instance** (`deploy()` function, lines 217-321):
- **Creation (new instances):**
  - Triggered when `AGENT_ENGINE_ID` is unset/empty
  - Uses `client.agent_engines.create()`
  - Returns resource name: `projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{ID}`

- **Update (existing instances):**
  - Triggered when `AGENT_ENGINE_ID` is set
  - Uses `client.agent_engines.update()`
  - Requires full resource name

- **Configuration:**
  - `agent`: AdkApp instance with root_agent
  - `staging_bucket`: `gs://{STAGING_BUCKET}`
  - `requirements`: List with wheel file name
  - `extra_packages`: List with wheel file name
  - `gcs_dir_name`: Subdirectory in staging bucket
  - `display_name`: Human-readable name
  - `description`: Agent description
  - `env_vars`: Runtime environment variables
  - `service_account`: App service account email
  - `enable_tracing`: True (enables OpenTelemetry)
  - `instrumentor_builder`: setup_opentelemetry function

**Wheel Package Management:**
- `get_wheel_file()` - Finds `*.whl` in current directory
- `delete_wheel_file()` - Cleanup after deployment
- Built by GitHub Actions: `uv build --wheel --out-dir .`

**Agent Deletion** (`delete()` function, lines 323-360):
- Requires `AGENT_ENGINE_ID`
- Uses `client.agent_engines.delete()`
- Interactive confirmation prompt
- Not used in CI/CD pipeline

#### register_agent.py

**Agentspace Registration** (`register()` function, lines 228-303):
- **API Endpoint Construction:**
  - Server selection based on `AGENTSPACE_APP_LOCATION` (global/us/eu)
  - Endpoint: `https://{SERVER}/{API_VERSION}/projects/{PROJECT}/locations/{LOCATION}/collections/default_collection/engines/{APP_ID}/assistants/default_assistant/agents`

- **Authentication:**
  - Uses `GCP_ACCESS_TOKEN` from GitHub Actions (OAuth 2.0)
  - Falls back to ADC (Application Default Credentials) for local use
  - Requires token for Discovery Engine REST API

- **Registration Logic:**
  - Lists existing registrations
  - Checks for duplicate `AGENT_ENGINE_ID`
  - Skips if already registered
  - POSTs agent definition if not found

- **Agent Definition Payload:**
  - `displayName`: Agent display name
  - `description`: Agent description
  - `adk_agent_definition.tool_settings.tool_description`: Tool description
  - `adk_agent_definition.provisioned_reasoning_engine.reasoning_engine`: Full resource name

**Agentspace Unregistration** (`unregister()` function, lines 305-367):
- Lists registrations
- Finds agent by `AGENT_ENGINE_ID`
- Interactive confirmation
- DELETE request to agent-specific endpoint

**List Registrations** (`list_agent_registrations()` function, lines 369-387):
- GET request to agents endpoint
- Parses and displays all registered agents
- Shows display name, registration ID, engine ID

### 1.3 Resources NOT Managed (Manual/External)

**Manual Prerequisites:**
- GCP Project creation
- Billing account linkage
- GitHub repository creation (from template)
- GitHub CLI authentication (`gh auth login`)
- Google Cloud CLI authentication (`gcloud auth login`, `gcloud auth application-default login`)
- Terraform installation
- UV package manager installation

**Default-Enabled APIs:**
These are enabled by default in new GCP projects, not explicitly managed:
- Compute Engine API
- Cloud Storage API
- Cloud Logging API
- Cloud Monitoring API

**External Dependencies:**
- Vertex AI model availability (gemini-2.5-flash)
- Python package dependencies (managed by UV/pyproject.toml)
- ADK (Agent Development Kit) library

---

## 2. "Setup Once" vs "Deploy Repeatedly" Resources

### 2.1 Setup Once (Infrastructure)

**Current Terraform Resources:**
- ✅ Service accounts (app, CI/CD)
- ✅ IAM roles and bindings
- ✅ Workload Identity Federation (pool, provider, bindings)
- ✅ API enablement
- ✅ GitHub repository secrets
- ✅ GitHub repository variables
- ✅ Environment variable validation

**Python Resources That Should Be "Setup Once":**
- ❌ **GCS staging bucket** - Should be Terraform-managed
  - Reason: Infrastructure component with security configuration
  - Current: Python creates on-demand if missing
  - Desired: Terraform creates with explicit configuration
  - Benefit: Explicit lifecycle, security settings, version control

**Borderline (Could Go Either Way):**
- 🤔 **Agent Engine instance** - Complex decision
  - Arguments for Terraform:
    - Infrastructure as code
    - Explicit state management
    - Predictable creation/updates
    - Version control for configuration changes
  - Arguments against Terraform:
    - Depends on wheel file (built by CI/CD)
    - Tightly coupled to application code
    - Frequent updates tied to code changes
    - Wheel file staging complexity
  - **Recommendation:** Start with Terraform for initial creation, evaluate update workflow

### 2.2 Deploy Repeatedly (Application Lifecycle)

**Should Remain in Deployment Scripts:**
- ✅ **Wheel package building** - Application packaging
  - Reason: Code artifact, not infrastructure
  - Managed by: UV build system
  - Triggered by: GitHub Actions workflow

- ✅ **Agentspace registration** - Application integration
  - Reason: Application-level concern, not infrastructure
  - Managed by: Python script (REST API calls)
  - Triggered by: GitHub Actions workflow (optional step)

- ✅ **Agent testing/validation** - Application verification
  - Scripts: `run_local_agent.py`, `run_remote_agent.py`
  - Purpose: Development and testing

**Currently "Deploy Repeatedly" but Should Be "Setup Once":**
- ❌ **Agent Engine instance creation** - Currently creates new instances without `AGENT_ENGINE_ID`
  - Problem: Easy to create orphaned instances
  - Solution: Terraform manages lifecycle, Python only updates
  - Benefit: Prevents resource sprawl, explicit management

---

## 3. Current Deployment Flow

### 3.1 Three-Phase Setup (Documented Workflow)

**Phase 1: Initial Terraform Setup**
```
User Action: Configure .env → terraform init → terraform plan → terraform apply
Terraform Creates:
  ├─ Service accounts (app, cicd)
  ├─ IAM roles and bindings
  ├─ Workload Identity Federation
  ├─ API enablement
  └─ GitHub secrets/variables

User Action: Trigger GitHub Actions (manual or git push)
GitHub Actions:
  ├─ Checkout code
  ├─ Authenticate to GCP (WIF + service account impersonation)
  ├─ Install UV + dependencies
  ├─ Build wheel package
  └─ Run Python deploy script

Python Script (deploy_agent.py):
  ├─ Validate environment variables
  ├─ Create/validate GCS bucket
  ├─ Find wheel file
  ├─ Create NEW Agent Engine instance (no AGENT_ENGINE_ID)
  └─ Output: Agent Engine resource name with ID

Result: First deployment complete, AGENT_ENGINE_ID captured in logs
```

**Phase 2: Enable Agent Engine Updates**
```
User Action: Capture AGENT_ENGINE_ID from logs → Update .env → terraform apply
Terraform Updates:
  └─ GitHub Actions variable: AGENT_ENGINE_ID

Result: Future deployments will UPDATE instead of CREATE
```

**Phase 3: Ongoing Development**
```
User Action: Code changes → git push → PR → merge to main
GitHub Actions:
  ├─ Build wheel
  └─ Run Python deploy script

Python Script (deploy_agent.py):
  ├─ Validate GCS bucket (already exists)
  ├─ Find wheel file
  ├─ UPDATE existing Agent Engine instance (AGENT_ENGINE_ID set)
  └─ Optional: Register with Agentspace

Result: Agent updated in place
```

### 3.2 GitHub Actions Workflow

**File:** `.github/workflows/deploy-to-agent-engine.yaml`

**Triggers:**
- Push to `main` branch
- Changes to: `src/**`, `terraform/**`, `uv.lock`
- Manual workflow dispatch

**Authentication:**
- Workload Identity Federation (no stored keys)
- Service account impersonation
- Generates OAuth 2.0 access token

**Steps:**
1. **Checkout code** - `actions/checkout@v5`
2. **Set up Python** - `actions/setup-python@v5` (version from pyproject.toml)
3. **Authenticate to GCP** - `google-github-actions/auth@v3`
   - Uses WIF provider (secret)
   - Impersonates CI/CD service account (secret)
   - Creates credentials file
   - Generates access token output
4. **Install UV** - `astral-sh/setup-uv@v6` (v0.8.21)
5. **Install dependencies** - `uv sync --frozen`
6. **Build wheel** - `uv build --wheel --out-dir .`
7. **Deploy agent** - `uv run deploy`
   - Environment: 10 variables from GitHub Actions
   - Service account: Implicitly via credentials file (ADC)
8. **Register with Agentspace** - `uv run register` (conditional)
   - Condition: All 3 required vars set (APP_ID, APP_LOCATION, ENGINE_ID)
   - Environment: 8 variables + access token

**Permissions:**
- `contents: read` - Read repository code
- `id-token: write` - Generate OIDC token for WIF

**Timeout:** 10 minutes

### 3.3 Authentication Flow

**GitHub Actions to Google Cloud:**
```
GitHub OIDC Token
  ↓ (Workload Identity Federation)
Google Security Token Service
  ↓ (Exchange for impersonation token)
CI/CD Service Account
  ↓ (Generate OAuth 2.0 access token)
Access Token
  ↓ (Used by)
├─ Application Default Credentials (deploy_agent.py)
└─ GCP_ACCESS_TOKEN env var (register_agent.py)
```

**Why Service Account Impersonation is Required:**
- Agentspace registration requires OAuth 2.0 access token
- Google GitHub Actions auth action only provides `access_token` output with service account impersonation
- Direct WIF does not expose access tokens
- See: `register_agent.py` line 131 (`setup_environment()` function)

---

## 4. Environment Variables Analysis

### 4.1 Terraform-Managed Variables

**Source:** `.env` file → Terraform → GitHub Actions variables

**Required Keys (Terraform validation):**
- `GOOGLE_GENAI_USE_VERTEXAI` - Must be "true"
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `GOOGLE_CLOUD_LOCATION` - Vertex AI region
- `GOOGLE_CLOUD_STORAGE_BUCKET` - Staging bucket name
- `AGENT_NAME` - Agent identifier

**Optional Keys (Synced if Present):**
- `GCS_DIR_NAME` - Subdirectory in staging bucket
- `AGENT_DISPLAY_NAME` - Human-readable name
- `AGENT_DESCRIPTION` - Agent description
- `AGENT_ENGINE_ID` - Existing instance ID (enables updates)
- `LOG_LEVEL` - Logging verbosity
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` - Trace content capture
- `AGENTSPACE_APP_ID` - Agentspace app ID
- `AGENTSPACE_APP_LOCATION` - Agentspace region

**Terraform-Only Variables (Not Synced to GitHub):**
- `GITHUB_REPO_NAME` - Repository name
- `GITHUB_REPO_OWNER` - GitHub username/org

### 4.2 Deployment Script Variables

**deploy_agent.py Required:**
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `GOOGLE_CLOUD_LOCATION` - Vertex AI region
- `GOOGLE_CLOUD_STORAGE_BUCKET` - Staging bucket name
- `AGENT_NAME` - Agent identifier

**deploy_agent.py Optional (with defaults):**
- `GCS_DIR_NAME` - Default: "agent-engine-staging"
- `AGENT_DISPLAY_NAME` - Default: "ADK Agent"
- `AGENT_DESCRIPTION` - Default: "ADK Agent"
- `AGENT_ENGINE_ID` - Default: None (triggers create instead of update)

**Derived/Computed:**
- `SERVICE_ACCOUNT` - `{AGENT_NAME}-app@{PROJECT}.iam.gserviceaccount.com`
- `ENABLE_TRACING` - Hardcoded: True
- `AGENT_ENV_VARS` - Dict of runtime environment variables:
  - `AGENT_NAME`
  - `LOG_LEVEL` (default: "INFO")
  - `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` (default: "true")

**register_agent.py Required:**
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `GOOGLE_CLOUD_LOCATION` - Vertex AI region
- `AGENT_ENGINE_ID` - Agent Engine instance ID
- `AGENTSPACE_APP_ID` - Agentspace app ID
- `AGENTSPACE_APP_LOCATION` - Agentspace region

**register_agent.py Optional:**
- `API_VERSION` - Default: "v1alpha"
- `AGENT_DISPLAY_NAME` - Default: "ADK Agent"
- `AGENT_DESCRIPTION` - Default: "ADK Agent"
- `GCP_ACCESS_TOKEN` - OAuth token (set by GitHub Actions)

**Derived/Computed:**
- `REASONING_ENGINE` - `projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}`
- `SERVER` - Based on AGENTSPACE_APP_LOCATION:
  - `global` → `discoveryengine.googleapis.com`
  - `us` → `us-discoveryengine.googleapis.com`
  - `eu` → `eu-discoveryengine.googleapis.com`
- `ENDPOINT` - Full API endpoint URL

### 4.3 Variables That Need to Move/Change

**For Terraform-Managed Agent Engine:**

**New Terraform Variables (Agent Engine Configuration):**
- `agent_staging_bucket_name` - GCS bucket (to be created by Terraform)
- `agent_staging_bucket_location` - Bucket region
- `agent_display_name` - Display name
- `agent_description` - Description
- `agent_gcs_dir_name` - Subdirectory in staging bucket
- `agent_runtime_env_vars` - Map of environment variables
- `agent_enable_tracing` - Enable OpenTelemetry

**Changed Behavior:**
- `AGENT_ENGINE_ID` - No longer optional
  - Current: Empty = create new instance
  - Terraform: Always set, managed by Terraform state
  - Impact: No more accidental instance creation

**Removed from Python Scripts:**
- Bucket creation logic (moved to Terraform)
- Agent Engine create/update logic (moved to Terraform)

**Remain in Python Scripts:**
- Wheel file discovery (application artifact)
- Agentspace registration (application integration)
- Agent testing/validation (development tooling)

---

## 5. Migration Gaps and Considerations

### 5.1 Critical Challenges

**1. Wheel File Dependency**
- **Problem:** Agent Engine requires wheel file at deployment time
- **Current:** Built by GitHub Actions, uploaded to GCS by Python SDK
- **Challenge:** Terraform needs to reference wheel file
- **Solutions:**
  - Option A: Terraform `null_resource` + `local-exec` to build wheel
  - Option B: GitHub Actions builds wheel, Terraform reads from GCS
  - Option C: Two-stage Terraform: infrastructure → application deployment
- **Recommendation:** Option C (separate workspaces or modules)

**2. Wheel File Upload to GCS**
- **Current:** Python SDK uploads wheel as part of `agent_engines.create()`
- **Challenge:** Terraform needs to stage wheel in GCS bucket
- **Solutions:**
  - `google_storage_bucket_object` resource
  - Requires wheel file path as input
  - Need to handle file naming (version/hash)
- **Consideration:** Wheel file changes frequently, triggers Terraform updates

**3. AdkApp Instance**
- **Problem:** `agent_engines.create()` requires AdkApp Python object
- **Challenge:** Terraform doesn't have direct Vertex AI Agent Engine resource
- **Solutions:**
  - Option A: Use `google_vertex_ai_endpoint` + reasoning engine API
  - Option B: Use `null_resource` with Python SDK call
  - Option C: Use Terraform `google_cloud_run_v2_job` for deployment
- **Recommendation:** Need to research Vertex AI Terraform provider capabilities

**4. Instrumentor Builder**
- **Problem:** `instrumentor_builder` parameter expects Python callable
- **Current:** `setup_opentelemetry` function from `agent.utils.observability`
- **Challenge:** How to pass Python function to Terraform-managed deployment
- **Solutions:**
  - Package in wheel, reference by import path
  - Agent Engine loads from wheel at runtime
- **Note:** This should work if wheel contains observability module

**5. State Synchronization**
- **Problem:** First deployment creates ID, must feed back to Terraform
- **Current:** Manual step (capture from logs, update .env, re-apply)
- **Challenge:** Chicken-and-egg problem for ID management
- **Solutions:**
  - Use Terraform outputs to capture Agent Engine ID
  - Eliminate manual step by managing in Terraform from start
- **Benefit:** No more Phase 2 manual sync

### 5.2 Moderate Challenges

**6. GitHub Actions Workflow Changes**
- **Current:** Workflow runs Python script
- **Proposed:** Workflow runs Terraform apply (for Agent Engine)
- **Considerations:**
  - Terraform state storage (local vs remote)
  - Terraform locking (prevent concurrent runs)
  - Terraform authentication (service account permissions)
  - Workflow becomes more complex

**7. GCS Bucket Security Configuration**
- **Current:** Python applies uniform bucket-level access + public access prevention
- **Terraform:** Need to explicitly configure:
  ```hcl
  resource "google_storage_bucket" "staging" {
    uniform_bucket_level_access = true
    public_access_prevention    = "enforced"
  }
  ```
- **Consideration:** Ensure Terraform matches current security posture

**8. Error Handling and Validation**
- **Current:** Python script validates environment, handles errors gracefully
- **Terraform:** Less flexible error handling
- **Need:** Validation blocks, precondition checks
- **Example:** Ensure service account exists before creating Agent Engine

**9. Dependency Ordering**
- **Current:** Python script enforces sequence (bucket → agent)
- **Terraform:** Need explicit `depends_on` for:
  - Service account must exist before Agent Engine
  - GCS bucket must exist before Agent Engine
  - APIs must be enabled before resource creation
- **Solution:** Use `depends_on` and implicit dependencies

**10. Update Detection**
- **Current:** Python checks if `AGENT_ENGINE_ID` is set
- **Terraform:** Uses state to track resources
- **Consideration:** How to handle changes to:
  - Display name/description (update in place)
  - Wheel file (replace or update?)
  - Environment variables (update in place)
- **Need:** Understand Agent Engine update semantics

### 5.3 Documentation and Workflow Changes

**11. README/Documentation Updates**
- Current 4-step quickstart assumes Python deployment
- Need to update for Terraform-managed Agent Engine
- New workflow:
  1. Setup (same)
  2. Develop/Prototype (same)
  3. Provision Infrastructure (expanded: includes Agent Engine)
  4. Trigger Updates (Terraform apply instead of Python script)

**12. Three-Phase Setup Elimination**
- **Current:** Phase 1 (initial), Phase 2 (capture ID), Phase 3 (ongoing)
- **Desired:** Two-phase (initial setup, ongoing development)
- **Benefit:** Simpler onboarding, fewer manual steps

**13. Developer Experience**
- **Current:** `uv run deploy` for manual deployment
- **Proposed:** `terraform -chdir=terraform apply`
- **Consideration:** Less intuitive for Python developers
- **Mitigation:** Wrapper scripts, clear documentation

### 5.4 Future Enhancements

**14. Remote State Management**
- **Current:** Local Terraform state
- **Desired:** Remote state (GCS backend)
- **Benefits:**
  - Team collaboration
  - State locking
  - Backup/recovery
- **Considerations:** Additional setup complexity

**15. Terraform Workspaces**
- **Use case:** Multiple environments (dev, staging, prod)
- **Current:** Single environment assumed
- **Enhancement:** Workspace-based configuration

**16. Agent Engine Updates via Terraform**
- **Challenge:** Frequent updates (every code change)
- **Question:** Is Terraform the right tool for frequent application updates?
- **Alternative:** Terraform for infrastructure, Python for updates
- **Hybrid:** Terraform creates, Python updates (needs investigation)

**17. Cost Optimization**
- **Current:** No cleanup of old Agent Engine instances
- **Enhancement:** Terraform manages lifecycle, explicit deletion
- **Benefit:** Prevent resource sprawl and unnecessary costs

---

## 6. Recommended Migration Strategy

### 6.1 Phase 1: GCS Bucket Migration (Low Risk)

**Goal:** Move GCS bucket creation from Python to Terraform

**Changes:**
1. Add `google_storage_bucket` resource to Terraform
2. Configure security settings (uniform access, public prevention)
3. Remove bucket creation logic from `deploy_agent.py`
4. Keep validation logic (confirm bucket exists)

**Benefits:**
- Explicit bucket management
- Version-controlled security configuration
- No impact on deployment workflow

**Testing:**
- Terraform import existing buckets
- Validate security settings match
- Test with new bucket creation

### 6.2 Phase 2: Agent Engine Initial Creation (Medium Risk)

**Goal:** Use Terraform to create Agent Engine instance on first deployment

**Approach:**
- Research Vertex AI Terraform provider capabilities
- Prototype Agent Engine resource configuration
- Handle wheel file dependency (manual or null_resource)
- Test create workflow end-to-end

**Considerations:**
- May need custom provider or null_resource
- Wheel file staging complexity
- AdkApp instantiation outside Python

**Success Criteria:**
- Agent Engine created by Terraform
- Observability working (trace, logs)
- Same functionality as Python script

### 6.3 Phase 3: Agent Engine Updates (High Risk)

**Goal:** Use Terraform to update existing Agent Engine instances

**Challenges:**
- Wheel file changes frequently
- Terraform state drift on code changes
- Update semantics (in-place vs replace)

**Options:**
- A: Full Terraform management (infrastructure + updates)
- B: Hybrid (Terraform creates, Python updates)
- C: Terraform triggers Python script (null_resource)

**Recommendation:** Start with Option B, evaluate Option A

### 6.4 Phase 4: Documentation and Developer Experience (Ongoing)

**Updates:**
- README quickstart workflow
- CI/CD setup guide (eliminate Phase 2)
- Environment variables reference
- Development guide
- Troubleshooting documentation

**Enhancements:**
- Wrapper scripts for common operations
- Validation/testing scripts
- Migration guide for existing deployments

---

## 7. Open Questions for Core Trio

### 7.1 Technical Decisions

1. **Vertex AI Terraform Support:**
   - Does the Google Terraform provider support Agent Engine/Reasoning Engine resources?
   - If not, what's the best approach (custom provider, null_resource, API calls)?

2. **Wheel File Management:**
   - Should Terraform manage wheel file lifecycle?
   - How to handle frequent wheel file updates?
   - Is two-stage deployment acceptable (infra → app)?

3. **Update Strategy:**
   - Should Terraform manage both create AND update?
   - Or Terraform creates, Python updates (hybrid)?
   - What are the trade-offs?

4. **State Management:**
   - Stay with local state or move to remote?
   - If remote, what backend (GCS, Terraform Cloud)?
   - Impact on GitHub Actions workflow?

### 7.2 Workflow Decisions

5. **Developer Experience:**
   - Is `terraform apply` acceptable for developers?
   - Should we provide wrapper scripts (`uv run deploy-terraform`)?
   - How to maintain consistency with existing commands?

6. **CI/CD Pipeline:**
   - Should GitHub Actions run Terraform or Python?
   - How to handle Terraform state locking in CI/CD?
   - Separate workflows for infrastructure vs application?

7. **Migration Path:**
   - Phased migration (bucket → agent create → agent update)?
   - All-at-once migration?
   - Support both approaches during transition?

### 7.3 Documentation and Support

8. **User Impact:**
   - How to migrate existing deployments?
   - Backward compatibility for Python scripts?
   - Support timeline for old workflow?

9. **Template Repository:**
   - Update template with new Terraform workflow?
   - Provide migration guide for existing users?
   - Version the template?

---

## Appendix A: File Locations Reference

### Terraform Files
- `terraform/github.tf` - GitHub secrets/variables management
- `terraform/iam.tf` - Service accounts, IAM roles, WIF
- `terraform/services.tf` - API enablement
- `terraform/locals.tf` - Local variable configuration
- `terraform/variables.tf` - Input variables
- `terraform/outputs.tf` - Output values
- `terraform/providers.tf` - Provider configuration
- `terraform/terraform.tf` - Terraform version constraints

### Python Deployment Scripts
- `src/deployment/deploy_agent.py` - Agent Engine deployment
- `src/deployment/register_agent.py` - Agentspace registration
- `src/deployment/run_local_agent.py` - Local development server
- `src/deployment/run_remote_agent.py` - Remote agent testing

### Agent Implementation
- `src/agent/agent.py` - Root agent definition
- `src/agent/tools.py` - Agent tools
- `src/agent/prompt.py` - System prompts
- `src/agent/utils/observability.py` - OpenTelemetry setup
- `src/agent/utils/logging_callbacks.py` - Logging utilities
- `src/agent/utils/custom_exporter.py` - Custom trace exporter

### GitHub Actions
- `.github/workflows/deploy-to-agent-engine.yaml` - Deployment workflow

### Configuration
- `.env.example` - Environment variable template
- `pyproject.toml` - Python project configuration
- `uv.lock` - Dependency lock file

### Documentation
- `README.md` - Main documentation
- `docs/cicd_setup_github_actions.md` - CI/CD setup guide
- `docs/environment_variables.md` - Environment variables reference
- `docs/development.md` - Development guide
- `docs/customizing_agent.md` - Agent customization guide
- `docs/observability.md` - Observability guide
- `docs/agentspace_registration.md` - Agentspace guide

---

## Appendix B: Environment Variable Cross-Reference

| Variable | Terraform | deploy_agent.py | register_agent.py | GitHub Actions |
|----------|-----------|-----------------|-------------------|----------------|
| AGENT_NAME | ✅ | ✅ | ❌ | ✅ |
| GOOGLE_CLOUD_PROJECT | ✅ | ✅ | ✅ | ✅ |
| GOOGLE_CLOUD_LOCATION | ✅ | ✅ | ✅ | ✅ |
| GOOGLE_CLOUD_STORAGE_BUCKET | ✅ | ✅ | ❌ | ✅ |
| GOOGLE_GENAI_USE_VERTEXAI | ✅ | ❌ | ❌ | ✅ |
| GITHUB_REPO_NAME | ✅ | ❌ | ❌ | ❌ |
| GITHUB_REPO_OWNER | ✅ | ❌ | ❌ | ❌ |
| GCS_DIR_NAME | ✅ (opt) | ✅ (opt) | ❌ | ✅ (opt) |
| AGENT_DISPLAY_NAME | ✅ (opt) | ✅ (opt) | ✅ (opt) | ✅ (opt) |
| AGENT_DESCRIPTION | ✅ (opt) | ✅ (opt) | ✅ (opt) | ✅ (opt) |
| AGENT_ENGINE_ID | ✅ (opt) | ✅ (opt) | ✅ | ✅ (opt) |
| LOG_LEVEL | ✅ (opt) | ✅ (opt) | ❌ | ✅ (opt) |
| OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT | ✅ (opt) | ✅ (opt) | ❌ | ✅ (opt) |
| AGENTSPACE_APP_ID | ✅ (opt) | ❌ | ✅ | ✅ (opt) |
| AGENTSPACE_APP_LOCATION | ✅ (opt) | ❌ | ✅ | ✅ (opt) |
| API_VERSION | ❌ | ❌ | ✅ (opt) | ❌ |
| GCP_ACCESS_TOKEN | ❌ | ❌ | ✅ (opt) | ✅ (generated) |
| GCP_WORKLOAD_IDENTITY_PROVIDER | ✅ (generated) | ❌ | ❌ | ✅ (secret) |
| GCP_SERVICE_ACCOUNT | ✅ (generated) | ❌ | ❌ | ✅ (secret) |

Legend:
- ✅ = Used/Required
- ✅ (opt) = Optional/Default available
- ✅ (generated) = Generated by tool
- ❌ = Not used

---

## Appendix C: Current vs Desired State Summary

### GCS Staging Bucket

| Aspect | Current (Python) | Desired (Terraform) |
|--------|------------------|---------------------|
| Creation | On-demand, runtime check | Explicit Terraform resource |
| Location | Optional parameter | Required configuration |
| Security | Hardcoded in Python | Explicit in Terraform |
| Lifecycle | Implicit (exists if needed) | Explicit management |
| Validation | Runtime error handling | Terraform plan validation |
| Documentation | In Python comments | In Terraform config |

### Agent Engine Instance

| Aspect | Current (Python) | Desired (Terraform) |
|--------|------------------|---------------------|
| Creation | Conditional (no AGENT_ENGINE_ID) | Terraform creates once |
| Updates | Conditional (AGENT_ENGINE_ID set) | TBD (Terraform or Python?) |
| ID Management | Manual (capture from logs) | Automatic (Terraform state) |
| Configuration | Python script parameters | Terraform variables |
| Wheel Dependency | Python SDK handles upload | Need staging strategy |
| Lifecycle | Create/update/delete via script | Terraform-managed lifecycle |

### Deployment Workflow

| Step | Current | Desired |
|------|---------|---------|
| 1. Initial Setup | Terraform (infra only) | Terraform (infra + GCS + Agent) |
| 2. Capture Agent ID | Manual (from logs) | Automatic (Terraform output) |
| 3. Sync Config | Manual (terraform apply) | Not needed (already in state) |
| 4. Deploy Updates | Python script | TBD (Terraform or Python?) |
| 5. Agentspace | Python script | Python script (unchanged) |

---

## Appendix D: Agent Engine Configuration Matrix

### Python SDK Parameters (Current)

```python
client.agent_engines.create(
    agent=adk_app,                    # AdkApp instance
    config={
        "staging_bucket": "gs://...",  # GCS bucket URI
        "requirements": ["wheel.whl"], # Wheel file name
        "extra_packages": ["wheel.whl"],# Wheel file name
        "gcs_dir_name": "staging",     # Subdirectory
        "display_name": "Agent",       # Display name
        "description": "Desc",         # Description
        "env_vars": {...},             # Runtime env vars
        "service_account": "email",    # Service account
    }
)
```

### AdkApp Parameters

```python
AdkApp(
    agent=root_agent,                        # Agent instance
    enable_tracing=True,                     # OpenTelemetry flag
    instrumentor_builder=setup_opentelemetry,# Callable function
)
```

### Terraform Resource (Proposed)

**Option 1: Native Resource (if available)**
```hcl
resource "google_vertex_ai_agent_engine" "main" {
  project         = var.project_id
  location        = var.location
  display_name    = var.agent_display_name
  description     = var.agent_description
  staging_bucket  = google_storage_bucket.staging.name
  # ... additional configuration
}
```

**Option 2: Null Resource with Python SDK**
```hcl
resource "null_resource" "agent_engine" {
  provisioner "local-exec" {
    command = "uv run deploy"
    environment = {
      AGENT_ENGINE_ID = ""  # Force create
    }
  }

  triggers = {
    wheel_hash = filemd5(var.wheel_file_path)
  }
}
```

**Option 3: REST API Call**
```hcl
resource "google_cloud_run_v2_job" "deploy_agent" {
  # Job that calls Vertex AI REST API
  # Requires wheel file staging
}
```

---

## Conclusion

This analysis documents the current Python-based deployment implementation and provides a foundation for migrating to Terraform-managed infrastructure. Key findings:

1. **Clear separation exists** between "setup once" (Terraform) and "deploy repeatedly" (Python) resources
2. **GCS bucket** should migrate to Terraform (low complexity)
3. **Agent Engine** migration is complex due to wheel file dependency and Python SDK usage
4. **Hybrid approach** (Terraform creates, Python updates) may be most pragmatic
5. **Significant workflow changes** will impact documentation and developer experience

The migration will eliminate manual steps (Phase 2 ID capture) but introduces new challenges around Terraform state management and wheel file handling. Recommend phased approach starting with GCS bucket migration.
