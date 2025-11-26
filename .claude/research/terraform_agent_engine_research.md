# Terraform `google_vertex_ai_reasoning_engine` Research Report

**Research Date:** 2025-10-09
**Terraform Provider:** hashicorp/google v7.6.0+
**Status:** Resource available as of September 26, 2025

---

## Executive Summary

The `google_vertex_ai_reasoning_engine` Terraform resource provides declarative infrastructure-as-code management for Vertex AI Agent Engine instances. This represents a significant shift from imperative Python SDK deployment to infrastructure-managed agent lifecycle.

**Key Capabilities:**
- Declarative agent deployment with state management
- Update-in-place support for existing instances (PATCH-based)
- Comprehensive configuration including encryption, service accounts, and secrets
- GCS-based package deployment (requirements.txt, pickle objects, dependencies)
- Built-in IAM permission propagation handling (5-minute wait recommendation)

**Migration Recommendation:** The Terraform resource is production-ready but requires architectural changes to package handling and state management workflows. The current Python-based deployment provides more flexibility for iterative development, while Terraform offers better infrastructure consistency and team collaboration.

---

## 1. Resource Overview

### Core Capabilities

The `google_vertex_ai_reasoning_engine` resource manages Vertex AI Reasoning Engine (Agent Engine) instances through Terraform's declarative model.

**Key Features:**
- **Async Operations**: Create/update/delete operations are asynchronous with long-running operation polling
- **Update Support**: Uses PATCH verb with update masks for in-place modifications
- **State Tracking**: Terraform state replaces manual `AGENT_ENGINE_ID` tracking
- **Import Support**: Can import existing instances into Terraform state
- **Region Immutability**: Region must be set at creation and cannot be changed

### Example Usage (Basic)

```hcl
resource "google_vertex_ai_reasoning_engine" "reasoning_engine" {
  display_name = "my-agent"
  description  = "A basic reasoning engine"
  region       = "us-central1"
}
```

### Example Usage (Full Configuration)

```hcl
locals {
  class_methods = [
    {
      api_mode    = "async"
      description = null
      name        = "async_query"
      parameters = {
        type       = "object"
        required   = []
        properties = {}
      }
    }
  ]
}

resource "google_vertex_ai_reasoning_engine" "reasoning_engine" {
  display_name = "production-agent"
  description  = "Production ADK agent with full configuration"
  region       = "us-central1"

  encryption_spec {
    kms_key_name = "projects/my-project/locations/us-central1/keyRings/my-kr/cryptoKeys/my-key"
  }

  spec {
    agent_framework = "google-adk"
    class_methods   = jsonencode(local.class_methods)
    service_account = google_service_account.agent_sa.email

    deployment_spec {
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      secret_env {
        name = "API_KEY"
        secret_ref {
          secret  = google_secret_manager_secret.api_key.secret_id
          version = "latest"
        }
      }
    }

    package_spec {
      dependency_files_gcs_uri = "gs://bucket/dependencies.tar.gz"
      pickle_object_gcs_uri    = "gs://bucket/code.pkl"
      python_version           = "3.12"
      requirements_gcs_uri     = "gs://bucket/requirements.txt"
    }
  }
}
```

---

## 2. Required vs Optional Arguments

### Required Arguments

Only **one** argument is truly required:

| Argument | Type | Description |
|----------|------|-------------|
| `display_name` | String | The display name of the ReasoningEngine |

### Optional Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `description` | String | - | Agent description |
| `region` | String | Provider default | GCP region (immutable after creation) |
| `project` | String | Provider default | GCP project ID |
| `encryption_spec` | Object | - | Customer-managed encryption key spec |
| `spec` | Object | - | Agent configuration (framework, packages, deployment) |

### `spec` Block Structure

The `spec` block contains all agent-specific configuration:

```hcl
spec {
  agent_framework = "google-adk"  # Optional: OSS framework identifier
  class_methods   = jsonencode([...])  # Optional: OpenAPI spec for methods
  service_account = "sa@project.iam.gserviceaccount.com"  # Optional

  deployment_spec {
    env { name = "VAR" value = "value" }  # Optional: Regular env vars
    secret_env { ... }  # Optional: Secret Manager references
  }

  package_spec {
    dependency_files_gcs_uri = "gs://..."  # Optional: tar.gz of dependencies
    pickle_object_gcs_uri    = "gs://..."  # Optional: pickled Python object
    python_version           = "3.12"       # Optional: Python runtime version
    requirements_gcs_uri     = "gs://..."  # Optional: requirements.txt
  }
}
```

---

## 3. Package Upload: Terraform vs Python SDK

### Current Python SDK Approach (deploy_agent.py)

**Workflow:**
1. Build wheel package locally: `uv build --wheel --out-dir .`
2. Python SDK auto-uploads wheel to GCS staging bucket
3. SDK handles pickle serialization and dependency bundling internally
4. Single `client.agent_engines.create()` or `.update()` call
5. Cleanup: Delete local wheel file

**Key Characteristics:**
- **Imperative**: Directly calls API with in-memory objects
- **Automatic Serialization**: ADK handles pickling the agent object
- **Simplified Dependencies**: Just pass wheel filename
- **Stateless**: Requires `AGENT_ENGINE_ID` for updates
- **Developer-Friendly**: Fast iteration with `uv run deploy`

**Code Example:**
```python
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
    instrumentor_builder=setup_opentelemetry,
)

remote_agent = client.agent_engines.create(
    agent=adk_app,
    config={
        "staging_bucket": f"gs://{STAGING_BUCKET}",
        "requirements": [wheel_file.name],  # Just the filename!
        "extra_packages": [wheel_file.name],
        "gcs_dir_name": GCS_DIR_NAME,
        "env_vars": AGENT_ENV_VARS,
        "service_account": SERVICE_ACCOUNT,
    },
)
```

### Terraform Approach

**Workflow:**
1. **Manual Preparation**: Build wheel, extract requirements, create pickle, bundle dependencies
2. **Upload to GCS**: Use `google_storage_bucket_object` resources for each artifact
3. **Reference in Terraform**: Point `package_spec` to GCS URIs
4. **Terraform Apply**: Declarative deployment with state tracking

**Key Characteristics:**
- **Declarative**: Infrastructure-as-code with state management
- **Manual Packaging**: Requires explicit artifact creation
- **GCS-First**: All artifacts must be pre-uploaded to GCS
- **Stateful**: Terraform tracks resource identity automatically
- **Team-Friendly**: Better for multi-developer environments

**Code Example:**
```hcl
# Step 1: Upload artifacts to GCS
resource "google_storage_bucket_object" "wheel" {
  name   = "agent-${var.version}.whl"
  bucket = google_storage_bucket.staging.id
  source = "./dist/agent.whl"
}

resource "google_storage_bucket_object" "requirements" {
  name   = "requirements.txt"
  bucket = google_storage_bucket.staging.id
  source = "./requirements.txt"
}

resource "google_storage_bucket_object" "pickle" {
  name   = "agent.pkl"
  bucket = google_storage_bucket.staging.id
  source = "./dist/agent.pkl"
}

resource "google_storage_bucket_object" "dependencies" {
  name   = "dependencies.tar.gz"
  bucket = google_storage_bucket.staging.id
  source = "./dist/dependencies.tar.gz"
}

# Step 2: Reference in agent engine
resource "google_vertex_ai_reasoning_engine" "agent" {
  spec {
    package_spec {
      dependency_files_gcs_uri = "${google_storage_bucket.staging.url}/${google_storage_bucket_object.dependencies.name}"
      pickle_object_gcs_uri    = "${google_storage_bucket.staging.url}/${google_storage_bucket_object.pickle.name}"
      python_version           = "3.12"
      requirements_gcs_uri     = "${google_storage_bucket.staging.url}/${google_storage_bucket_object.requirements.name}"
    }
  }
}
```

### Key Differences

| Aspect | Python SDK | Terraform |
|--------|-----------|-----------|
| **Packaging** | ADK auto-handles | Manual artifact creation |
| **Upload** | Automatic to staging bucket | Explicit GCS resources |
| **Pickle Creation** | SDK serializes agent | Must create `.pkl` manually |
| **Dependencies** | Wheel includes everything | Separate tar.gz required |
| **State** | Manual tracking via `AGENT_ENGINE_ID` | Automatic in Terraform state |
| **Updates** | Check if ID exists, call update/create | Terraform detects drift automatically |
| **Iteration Speed** | Fast (single command) | Slower (terraform plan/apply) |

### Migration Challenge: Pickle Creation

The **biggest gap** is pickle file creation. The current Python SDK workflow doesn't expose the pickle step:

**Current (SDK handles internally):**
```python
adk_app = AdkApp(agent=root_agent, ...)
# SDK pickles this automatically during deployment
```

**Terraform requires:**
```python
# Must create pickle manually before Terraform
import cloudpickle
from agent.agent import root_agent

with open("agent.pkl", "wb") as f:
    cloudpickle.dump(root_agent, f)
```

**Note from Terraform docs:**
```python
# Generate pickle files with the cloudpickle library:
local_agent = LangchainAgent(
  model=MODEL,
  agent_executor_kwargs={"return_intermediate_steps": True},
)

output_filename = "pickle.pkl"
with open(output_filename, "wb") as f:
  cloudpickle.dump(local_agent, f)
```

---

## 4. State Management: Terraform vs AGENT_ENGINE_ID

### Current Approach: Manual State Tracking

**Environment Variable Based:**
```bash
# Initial deployment (no AGENT_ENGINE_ID set)
uv run deploy  # Creates new instance

# Capture ID from output
AGENT_ENGINE_ID="1234567890"  # Manual step!

# Subsequent deployments
export AGENT_ENGINE_ID="1234567890"
uv run deploy  # Updates existing instance
```

**Python Logic:**
```python
if AGENT_ENGINE_ID:
    remote_agent = client.agent_engines.update(
        name=f"projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}",
        agent=adk_app,
        config={...},
    )
else:
    remote_agent = client.agent_engines.create(
        agent=adk_app,
        config={...},
    )
```

**Problems with Current Approach:**
- **Manual Tracking**: User must capture and store `AGENT_ENGINE_ID`
- **Environment Drift**: `.env` file can desync from actual infrastructure
- **No History**: No record of previous configurations or changes
- **Team Coordination**: Hard to share state across developers
- **Error-Prone**: Easy to forget to set `AGENT_ENGINE_ID` and create duplicates

### Terraform Approach: Automatic State Management

**Terraform State File:**
```json
{
  "resources": [
    {
      "type": "google_vertex_ai_reasoning_engine",
      "name": "agent",
      "instances": [
        {
          "attributes": {
            "id": "projects/my-project/locations/us-central1/reasoningEngines/1234567890",
            "name": "1234567890",
            "display_name": "my-agent",
            "region": "us-central1"
          }
        }
      ]
    }
  ]
}
```

**Benefits:**
- **Automatic Tracking**: Terraform state file tracks all resource IDs
- **Drift Detection**: `terraform plan` shows differences between config and reality
- **Version History**: Terraform state can be versioned in remote backends
- **Team Collaboration**: Remote state (GCS, S3) enables team workflows
- **Idempotent**: Running `terraform apply` multiple times is safe

**Workflow:**
```bash
# Initial deployment
terraform apply  # Creates agent, stores ID in state

# Update configuration in .tf file
# Terraform automatically knows which resource to update
terraform apply  # Updates existing agent (no manual ID tracking!)

# View current state
terraform show

# Import existing agent (if created outside Terraform)
terraform import google_vertex_ai_reasoning_engine.agent \
  projects/my-project/locations/us-central1/reasoningEngines/1234567890
```

### Hybrid Approach for This Repository

**Challenge:** The template repository supports two workflows:
1. Quick prototyping: Clone directly, test locally (no CI/CD)
2. Production: Create from template, set up CI/CD

**Recommendation:**
- **Keep Python SDK deployment** for local development and prototyping
- **Add Terraform option** for production infrastructure management
- **Document both paths** clearly in README

**Why Keep Both:**
- Python SDK: Fast iteration during development (`uv run deploy`)
- Terraform: Stable infrastructure for production (CI/CD managed)
- Gradual migration path for existing users

---

## 5. Update vs Create Behavior

### Terraform Update Mechanism

**Resource Definition:**
```yaml
# From Magic Modules configuration
update_verb: 'PATCH'
update_mask: true
async:
  actions: ['create', 'delete', 'update']
  type: 'OpAsync'
```

**How Terraform Handles Updates:**

1. **Detect Changes**: Compare desired state (`.tf` config) vs actual state (Terraform state + API)
2. **Generate Plan**: Identify which fields changed
3. **Update Mask**: Send PATCH request with only changed fields
4. **Async Polling**: Wait for long-running operation to complete
5. **Update State**: Refresh Terraform state with new values

**Example Update Workflow:**
```hcl
# Initial configuration
resource "google_vertex_ai_reasoning_engine" "agent" {
  display_name = "my-agent"
  description  = "Version 1.0"
  region       = "us-central1"
}

# After terraform apply, change description
resource "google_vertex_ai_reasoning_engine" "agent" {
  display_name = "my-agent"
  description  = "Version 2.0"  # Changed!
  region       = "us-central1"
}

# terraform plan output:
# ~ update in-place
# ~ description: "Version 1.0" -> "Version 2.0"
```

**Supported Update Operations:**
- Display name
- Description
- Environment variables (`deployment_spec.env`)
- Secret environment variables (`deployment_spec.secret_env`)
- Package artifacts (new GCS URIs)
- Python version
- Agent framework
- Class methods
- Service account

**Immutable Fields (Require Replacement):**
- `region`: Cannot change after creation
- `encryption_spec.kms_key_name`: Immutable encryption key

**Replacement Behavior:**
```hcl
# Changing region triggers resource replacement
# ~ forces replacement
# - delete
# + create
```

### Python SDK Update Behavior

**Current Implementation:**
```python
if AGENT_ENGINE_ID:
    remote_agent = client.agent_engines.update(
        name=f"projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}",
        agent=adk_app,  # Full agent object
        config={...},   # All configuration parameters
    )
```

**Key Differences:**
- **Full Replacement**: Python SDK may send entire configuration (not just delta)
- **No Drift Detection**: Can't tell what changed before applying
- **Manual ID Management**: User must provide correct resource name
- **Immediate Execution**: No planning phase, changes applied immediately

---

## 6. Service Account Integration

### Terraform IAM Wiring

Terraform provides comprehensive service account and IAM management alongside the agent engine resource.

**Complete Example:**
```hcl
# 1. Create service account
resource "google_service_account" "agent_sa" {
  account_id   = "agent-engine-sa"
  display_name = "Agent Engine Service Account"
  description  = "Service account for Vertex AI Agent Engine"
}

# 2. Grant required IAM roles
resource "google_project_iam_member" "agent_storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = google_service_account.agent_sa.member
}

resource "google_project_iam_member" "agent_ai_platform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.agent_sa.member
}

resource "google_project_iam_member" "agent_viewer" {
  project = var.project_id
  role    = "roles/viewer"
  member  = google_service_account.agent_sa.member
}

# 3. Grant access to secrets (if using secret_env)
resource "google_secret_manager_secret_iam_member" "agent_secret_access" {
  secret_id = google_secret_manager_secret.api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.agent_sa.member
}

# 4. Wait for IAM propagation (CRITICAL!)
resource "time_sleep" "wait_for_iam" {
  create_duration = "5m"

  depends_on = [
    google_project_iam_member.agent_storage_viewer,
    google_project_iam_member.agent_ai_platform_user,
    google_project_iam_member.agent_viewer,
    google_secret_manager_secret_iam_member.agent_secret_access,
  ]
}

# 5. Create agent engine (depends on IAM propagation)
resource "google_vertex_ai_reasoning_engine" "agent" {
  display_name = "my-agent"
  region       = "us-central1"

  spec {
    service_account = google_service_account.agent_sa.email
    # ...
  }

  depends_on = [time_sleep.wait_for_iam]
}
```

### Required IAM Roles

**For Agent Service Account:**
| Role | Purpose |
|------|---------|
| `roles/storage.objectViewer` | Read packages from GCS staging bucket |
| `roles/aiplatform.user` | Use Vertex AI extensions and features |
| `roles/viewer` | General GCP resource viewing (recommended) |
| `roles/secretmanager.secretAccessor` | Access secrets referenced in `secret_env` |

**For Terraform Service Account (deployment):**
| Role | Purpose |
|------|---------|
| `roles/aiplatform.admin` | Create/update/delete agent engines |
| `roles/storage.admin` | Manage GCS staging bucket and objects |
| `roles/iam.serviceAccountUser` | Impersonate agent service account |
| `roles/resourcemanager.projectIamAdmin` | Grant IAM roles (if Terraform manages IAM) |

### IAM Propagation Wait Time

**Critical Requirement:**
```hcl
# Terraform official example includes 5-minute wait
resource "time_sleep" "wait_5_minutes" {
  create_duration = "5m"
  depends_on = [
    google_project_iam_member.sa_iam_ai_platform_user,
    google_project_iam_member.sa_iam_object_viewer,
    google_project_iam_member.sa_iam_viewer,
    google_secret_manager_secret_iam_member.secret_access,
  ]
}
```

**Why 5 Minutes?**
- IAM permissions can take several minutes to propagate globally
- Agent Engine deployment may fail if permissions not yet active
- Documented best practice from Google's official examples
- Alternative: Use `google_project_service` with `disable_on_destroy = false`

### Current Repository Approach

**Terraform-Managed (Phase 1):**
```hcl
# terraform/service_accounts.tf
resource "google_service_account" "agent_engine" {
  account_id   = "${var.agent_name}-app"
  display_name = "${var.agent_name} Agent Engine Service Account"
  description  = "Service account for ${var.agent_name} agent engine deployment"
}

# IAM roles granted
resource "google_project_iam_member" "agent_engine_aiplatform_user" { ... }
resource "google_project_iam_member" "agent_engine_storage_object_viewer" { ... }
resource "google_project_iam_member" "agent_engine_logging_log_writer" { ... }
```

**Python SDK Uses (Phase 2):**
```python
# src/deployment/deploy_agent.py
SERVICE_ACCOUNT = f"{AGENT_NAME}-app@{PROJECT}.iam.gserviceaccount.com"

remote_agent = client.agent_engines.create(
    agent=adk_app,
    config={
        "service_account": SERVICE_ACCOUNT,
        # ...
    },
)
```

**Migration Path:**
- Terraform creates service account + IAM roles
- Python SDK or Terraform references service account
- Both approaches use same infrastructure

---

## 7. Known Limitations and Issues

### Limitations from Implementation

1. **Immutable Encryption:**
   ```yaml
   # From ReasoningEngine.yaml
   encryptionSpec:
     immutable: true
   ```
   Cannot change KMS key after creation. Requires resource replacement.

2. **Immutable Region:**
   ```yaml
   parameters:
     - name: 'region'
       immutable: true
   ```
   Cannot move agent between regions. Requires recreation.

3. **No Direct Wheel Support:**
   - Terraform only supports GCS URIs in `package_spec`
   - Cannot directly reference local wheel files
   - Must upload artifacts to GCS first

4. **Pickle File Requirement:**
   - Documentation shows pickle-based deployment
   - ADK SDK auto-generates pickle, but Terraform requires pre-created file
   - No native wheel-only deployment path in Terraform

5. **Async Operation Timeouts:**
   ```yaml
   timeouts:
     insert_minutes: 20
     update_minutes: 20
     delete_minutes: 20
   ```
   Long-running operations can timeout. Configurable but default is 20 minutes.

6. **IAM Propagation Delays:**
   - Requires explicit 5-minute wait in Terraform
   - No built-in retry mechanism
   - Must use `time_sleep` resource

### Issues from PR Discussion

**From hashicorp/terraform-provider-google#24512:**
- Derived from Magic Modules PR (GoogleCloudPlatform/magic-modules#14480)
- Automated generation (Modular Magician bot)
- No significant discussion or known issues mentioned in PR

**Testing Coverage:**
- Tests include basic create and full update scenarios
- Tests verify import functionality
- Tests confirm encryption spec immutability
- Tests validate IAM permission propagation

### Potential Issues (Not Documented)

1. **State Drift:**
   - If agent modified via Python SDK or Console, Terraform won't know
   - Next `terraform apply` may overwrite manual changes
   - Recommendation: Choose either Terraform or SDK, not both

2. **Pickle Compatibility:**
   - `cloudpickle` version mismatches between build and runtime
   - Python version differences (3.11 vs 3.12 vs 3.13)
   - ADK version compatibility

3. **GCS Artifact Lifecycle:**
   - Terraform doesn't auto-cleanup old package versions
   - Can accumulate stale artifacts in staging bucket
   - Recommendation: Use lifecycle policies on GCS bucket

4. **Import Limitations:**
   - Can import existing agent, but must reconstruct full configuration
   - No auto-generated config from existing resource
   - May require trial and error to match actual state

---

## 8. Migration Considerations

### From Python SDK to Terraform

**Key Challenges:**

1. **Packaging Workflow Change**
   ```python
   # Before (Python SDK - automatic):
   uv build --wheel --out-dir .
   uv run deploy  # SDK handles everything

   # After (Terraform - manual):
   uv build --wheel --out-dir .
   python scripts/create_pickle.py  # New step!
   tar -czf dependencies.tar.gz ...  # New step!
   terraform apply  # References pre-uploaded artifacts
   ```

2. **State Migration**
   ```bash
   # Option 1: Import existing agent
   terraform import google_vertex_ai_reasoning_engine.agent \
     projects/my-project/locations/us-central1/reasoningEngines/1234567890

   # Option 2: Recreate agent with Terraform
   # Delete existing via Python SDK
   export AGENT_ENGINE_ID=1234567890
   uv run delete

   # Create with Terraform
   terraform apply
   ```

3. **CI/CD Pipeline Changes**
   ```yaml
   # Before (GitHub Actions):
   - name: Build wheel
     run: uv build --wheel --out-dir .
   - name: Deploy
     run: uv run deploy

   # After (Terraform):
   - name: Build artifacts
     run: |
       uv build --wheel --out-dir .
       python scripts/create_pickle.py
       tar -czf dependencies.tar.gz dist/
   - name: Upload to GCS
     run: |
       gsutil cp dist/*.whl gs://bucket/
       gsutil cp dist/agent.pkl gs://bucket/
       gsutil cp dependencies.tar.gz gs://bucket/
       gsutil cp requirements.txt gs://bucket/
   - name: Terraform apply
     run: terraform apply -auto-approve
   ```

4. **Environment Variable Mapping**
   ```python
   # Before (Python):
   AGENT_ENV_VARS = {
       "AGENT_NAME": AGENT_NAME,
       "LOG_LEVEL": safe_getenv("LOG_LEVEL", "INFO"),
   }

   # After (Terraform):
   spec {
     deployment_spec {
       env {
         name  = "AGENT_NAME"
         value = var.agent_name
       }
       env {
         name  = "LOG_LEVEL"
         value = var.log_level
       }
     }
   }
   ```

### Recommendation: Hybrid Approach

**For this template repository, recommend:**

1. **Keep Python SDK for Development:**
   - Fast iteration: `uv run deploy`
   - Local testing with `uv run local-agent`
   - Developer-friendly error messages
   - No complex packaging steps

2. **Add Terraform Option for Production:**
   - Infrastructure-as-code for production deployments
   - Team collaboration with remote state
   - Drift detection and version history
   - Better integration with existing Terraform infrastructure

3. **Document Both Paths:**
   ```markdown
   ## Deployment Options

   ### Option A: Python SDK (Recommended for Development)
   Quick iteration and prototyping:
   ```bash
   uv build --wheel --out-dir .
   uv run deploy
   ```

   ### Option B: Terraform (Recommended for Production)
   Infrastructure-as-code with state management:
   ```bash
   terraform -chdir=terraform/agent-engine apply
   ```
   ```

4. **Migration Guide:**
   - Start with Python SDK for initial development
   - Once agent is stable, migrate to Terraform
   - Use `terraform import` to bring existing agent under Terraform management
   - Update CI/CD to use Terraform for production deployments

### Architecture Decision

**Factors to Consider:**

| Factor | Python SDK | Terraform |
|--------|-----------|-----------|
| **Development Speed** | ⭐⭐⭐⭐⭐ Fast | ⭐⭐⭐ Medium |
| **Production Stability** | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |
| **Team Collaboration** | ⭐⭐ Fair | ⭐⭐⭐⭐⭐ Excellent |
| **State Management** | ⭐⭐ Manual | ⭐⭐⭐⭐⭐ Automatic |
| **Ease of Use** | ⭐⭐⭐⭐⭐ Simple | ⭐⭐⭐ Moderate |
| **Infrastructure Integration** | ⭐⭐ Limited | ⭐⭐⭐⭐⭐ Seamless |
| **Packaging Complexity** | ⭐⭐⭐⭐⭐ Automatic | ⭐⭐ Manual |

### Migration Checklist

If migrating from Python SDK to Terraform:

- [ ] **Review current deployment flow** in `deploy_agent.py`
- [ ] **Create pickle generation script** (currently handled by ADK automatically)
- [ ] **Create dependency bundling script** (tar.gz creation)
- [ ] **Set up GCS artifact storage** (if not using existing staging bucket)
- [ ] **Write Terraform configuration** for `google_vertex_ai_reasoning_engine`
- [ ] **Import existing agent** (if preserving current instance)
- [ ] **Test Terraform plan/apply** in non-production environment
- [ ] **Update CI/CD pipeline** to use Terraform
- [ ] **Configure remote state backend** (GCS recommended)
- [ ] **Update documentation** with new deployment workflow
- [ ] **Add IAM propagation wait** (`time_sleep` resource)
- [ ] **Test rollback procedures** (Terraform state recovery)

---

## 9. Code Examples and Comparisons

### Complete Python SDK Deployment (Current)

```python
# src/deployment/deploy_agent.py
from agent.agent import root_agent
from agent.utils.observability import setup_opentelemetry
from vertexai.agent_engines import AdkApp

# Get wheel file
wheel_file = next(Path().glob("*.whl"))

# Create ADK app with observability
adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
    instrumentor_builder=setup_opentelemetry,
)

# Deploy
if AGENT_ENGINE_ID:
    remote_agent = client.agent_engines.update(
        name=f"projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}",
        agent=adk_app,
        config={
            "staging_bucket": f"gs://{STAGING_BUCKET}",
            "requirements": [wheel_file.name],
            "extra_packages": [wheel_file.name],
            "gcs_dir_name": GCS_DIR_NAME,
            "display_name": AGENT_DISPLAY_NAME,
            "description": AGENT_DESCRIPTION,
            "env_vars": AGENT_ENV_VARS,
            "service_account": SERVICE_ACCOUNT,
        },
    )
else:
    remote_agent = client.agent_engines.create(
        agent=adk_app,
        config={...},  # Same config
    )

print(f"🤖 Agent engine resource: {remote_agent.api_resource.name}")
```

### Equivalent Terraform Configuration

```hcl
# terraform/agent-engine/main.tf

# Variables
variable "project_id" { type = string }
variable "location" { type = string }
variable "staging_bucket" { type = string }
variable "agent_name" { type = string }
variable "agent_version" { type = string }
variable "log_level" { default = "INFO" }

# Storage bucket for artifacts
resource "google_storage_bucket" "staging" {
  name                        = var.staging_bucket
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
}

# Upload wheel package
resource "google_storage_bucket_object" "wheel" {
  name   = "agent-${var.agent_version}.whl"
  bucket = google_storage_bucket.staging.id
  source = "../dist/agent-${var.agent_version}.whl"
}

# Upload requirements.txt
resource "google_storage_bucket_object" "requirements" {
  name   = "requirements.txt"
  bucket = google_storage_bucket.staging.id
  source = "../requirements.txt"
}

# Upload pickle file (must be created manually!)
resource "google_storage_bucket_object" "pickle" {
  name   = "agent-${var.agent_version}.pkl"
  bucket = google_storage_bucket.staging.id
  source = "../dist/agent-${var.agent_version}.pkl"
}

# Upload dependencies tar.gz (must be created manually!)
resource "google_storage_bucket_object" "dependencies" {
  name   = "dependencies-${var.agent_version}.tar.gz"
  bucket = google_storage_bucket.staging.id
  source = "../dist/dependencies-${var.agent_version}.tar.gz"
}

# Service account
resource "google_service_account" "agent" {
  account_id   = "${var.agent_name}-app"
  display_name = "${var.agent_name} Agent Engine Service Account"
}

# IAM roles
resource "google_project_iam_member" "agent_storage" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = google_service_account.agent.member
}

resource "google_project_iam_member" "agent_ai_platform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.agent.member
}

resource "google_project_iam_member" "agent_viewer" {
  project = var.project_id
  role    = "roles/viewer"
  member  = google_service_account.agent.member
}

# Wait for IAM propagation
resource "time_sleep" "iam_wait" {
  create_duration = "5m"
  depends_on = [
    google_project_iam_member.agent_storage,
    google_project_iam_member.agent_ai_platform,
    google_project_iam_member.agent_viewer,
  ]
}

# Class methods configuration
locals {
  class_methods = [
    {
      api_mode    = "async"
      description = null
      name        = "async_query"
      parameters = {
        type       = "object"
        required   = []
        properties = {}
      }
    }
  ]
}

# Agent Engine
resource "google_vertex_ai_reasoning_engine" "agent" {
  display_name = "${var.agent_name} ADK Agent"
  description  = "ADK Agent v${var.agent_version}"
  region       = var.location

  spec {
    agent_framework = "google-adk"
    class_methods   = jsonencode(local.class_methods)
    service_account = google_service_account.agent.email

    deployment_spec {
      env {
        name  = "AGENT_NAME"
        value = var.agent_name
      }

      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }

      env {
        name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
        value = "true"
      }
    }

    package_spec {
      dependency_files_gcs_uri = "${google_storage_bucket.staging.url}/${google_storage_bucket_object.dependencies.name}"
      pickle_object_gcs_uri    = "${google_storage_bucket.staging.url}/${google_storage_bucket_object.pickle.name}"
      python_version           = "3.12"
      requirements_gcs_uri     = "${google_storage_bucket.staging.url}/${google_storage_bucket_object.requirements.name}"
    }
  }

  depends_on = [time_sleep.iam_wait]
}

# Outputs
output "agent_engine_id" {
  value       = google_vertex_ai_reasoning_engine.agent.name
  description = "Full resource name of the agent engine"
}

output "agent_engine_short_id" {
  value       = basename(google_vertex_ai_reasoning_engine.agent.name)
  description = "Short ID for AGENT_ENGINE_ID environment variable"
}
```

### Required Manual Packaging Script

```python
# scripts/create_deployment_artifacts.py
"""Create deployment artifacts for Terraform-based deployment."""

import cloudpickle
import tarfile
from pathlib import Path

# Create pickle file
from agent.agent import root_agent
from agent.utils.observability import setup_opentelemetry
from vertexai.agent_engines import AdkApp

adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
    instrumentor_builder=setup_opentelemetry,
)

# Note: We pickle the AdkApp, not just root_agent
with open("dist/agent.pkl", "wb") as f:
    cloudpickle.dump(adk_app, f)

print("✅ Created pickle file: dist/agent.pkl")

# Create dependencies tar.gz
# This would include any additional files needed at runtime
with tarfile.open("dist/dependencies.tar.gz", "w:gz") as tar:
    # Add any additional dependencies here
    # For ADK, this might be empty if everything is in the wheel
    pass

print("✅ Created dependencies archive: dist/dependencies.tar.gz")
```

---

## Appendix A: Resource API Reference

### Full Argument Reference

```hcl
resource "google_vertex_ai_reasoning_engine" "example" {
  # Required
  display_name = string

  # Optional
  description = string
  region      = string  # Immutable
  project     = string

  # Optional: Encryption
  encryption_spec {
    kms_key_name = string  # Immutable
  }

  # Optional: Agent specification
  spec {
    agent_framework = string
    class_methods   = string  # JSON-encoded
    service_account = string

    deployment_spec {
      env {
        name  = string
        value = string
      }

      secret_env {
        name = string
        secret_ref {
          secret  = string
          version = string  # Optional
        }
      }
    }

    package_spec {
      dependency_files_gcs_uri = string
      pickle_object_gcs_uri    = string
      python_version           = string
      requirements_gcs_uri     = string
    }
  }

  # Optional: Dependencies
  depends_on = [...]

  # Optional: Lifecycle
  lifecycle {
    prevent_destroy = bool
    ignore_changes  = [...]
  }

  # Optional: Timeouts
  timeouts {
    create = string
    update = string
    delete = string
  }
}
```

### Computed Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | String | Full resource name format |
| `name` | String | Generated reasoning engine name |
| `create_time` | String | RFC3339 timestamp |
| `update_time` | String | RFC3339 timestamp |

### Import Formats

```bash
# Format 1: Full resource name
terraform import google_vertex_ai_reasoning_engine.default \
  projects/my-project/locations/us-central1/reasoningEngines/1234567890

# Format 2: Project/Region/Name
terraform import google_vertex_ai_reasoning_engine.default \
  my-project/us-central1/1234567890

# Format 3: Region/Name (uses provider project)
terraform import google_vertex_ai_reasoning_engine.default \
  us-central1/1234567890

# Format 4: Name only (uses provider project and region)
terraform import google_vertex_ai_reasoning_engine.default \
  1234567890
```

---

## Appendix B: References

### Official Documentation
- [Terraform Resource: google_vertex_ai_reasoning_engine](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/vertex_ai_reasoning_engine)
- [Vertex AI Agent Engine Quickstart](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/quickstart)
- [Vertex AI REST API: ReasoningEngine](https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.reasoningEngines/)

### Pull Requests
- [terraform-provider-google PR #24512](https://github.com/hashicorp/terraform-provider-google/pull/24512) - Add reasoning engine resource
- [magic-modules PR #14480](https://github.com/GoogleCloudPlatform/magic-modules/pull/14480) - Implementation source

### Implementation Files
- `mmv1/products/vertexai/ReasoningEngine.yaml` - Resource definition
- `mmv1/templates/terraform/examples/vertex_ai_reasoning_engine_*.tf.tmpl` - Example configurations
- `mmv1/third_party/terraform/services/vertexai/resource_vertex_ai_reasoning_engine_test.go` - Test suite

---

## Summary and Recommendations

### For Immediate Use

**Recommended Approach:**
1. **Keep current Python SDK workflow** for primary deployment
2. **Add Terraform as optional path** for teams preferring IaC
3. **Document both approaches** in README with clear use cases
4. **Create helper scripts** for artifact preparation if adding Terraform support

### For Future Consideration

**Long-term migration path:**
1. **Phase 1**: Add Terraform option alongside Python SDK
2. **Phase 2**: Migrate CI/CD to Terraform for production deployments
3. **Phase 3**: Use Python SDK for development, Terraform for production
4. **Phase 4**: Evaluate full migration based on user feedback

### Key Takeaways

1. **Terraform resource is production-ready** (merged Sep 2025)
2. **Manual packaging is required** - biggest difference from Python SDK
3. **State management is superior** in Terraform but adds complexity
4. **IAM propagation delays are critical** - must wait 5 minutes
5. **Update mechanism is robust** - PATCH-based with async operations
6. **Service account integration is comprehensive** with full Terraform support

The choice between Python SDK and Terraform should be based on team workflow, infrastructure maturity, and deployment frequency. Both are valid approaches with different trade-offs.
