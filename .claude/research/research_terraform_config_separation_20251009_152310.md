# Terraform Configuration Separation: One-Time CI/CD Setup vs Ongoing Deployment

**Research Date:** 2025-10-09
**Author:** Production Systems Research Expert
**Context:** Separating Terraform configurations for Google Cloud AI Agent Engine deployment infrastructure

---

## Executive Summary

This research investigates best practices for separating Terraform configurations into two distinct concerns:

1. **One-time CI/CD setup resources** - Infrastructure provisioned once and rarely changed (GitHub secrets/variables, Workload Identity Federation, base service accounts, API enablement)
2. **Per-deployment resources** - Application-specific resources managed with each deployment (Agent Engine instances, versioned resources, deployment-specific IAM)

### Key Recommendations

**Recommended Approach:** **Separate Root Modules with Remote State Sharing**

- **Setup Module** (`terraform/setup/`): One-time CI/CD infrastructure
- **Deployment Module** (`terraform/deployment/`): Per-deployment Agent Engine resources
- **State Backend**: Google Cloud Storage for remote state with locking
- **Data Flow**: Use `terraform_remote_state` data source to reference setup outputs in deployment
- **CI/CD Integration**: GitHub Actions workflow runs deployment Terraform on main branch merges

**Why this approach:**
- Clear separation of concerns and lifecycles
- Independent state files prevent accidental infrastructure destruction
- Setup resources remain stable while deployment resources can be recreated/destroyed freely
- Enables multiple deployment environments (dev/staging/prod) sharing the same CI/CD setup
- Aligns with Terraform best practices for managing infrastructure at different lifecycles

---

## Table of Contents

1. [Current Architecture Analysis](#current-architecture-analysis)
2. [Terraform Workspace Strategies](#terraform-workspace-strategies)
3. [Recommended Directory Structure](#recommended-directory-structure)
4. [Remote State Backend Configuration](#remote-state-backend-configuration)
5. [State Data Sharing Between Modules](#state-data-sharing-between-modules)
6. [GitHub Actions Integration Patterns](#github-actions-integration-patterns)
7. [Migration Path from Current Setup](#migration-path-from-current-setup)
8. [Trade-offs and Considerations](#trade-offs-and-considerations)
9. [Implementation Checklist](#implementation-checklist)
10. [References and Best Practices](#references-and-best-practices)

---

## Current Architecture Analysis

### Existing Terraform Configuration

The current implementation uses a **monolithic single root module** approach:

```
terraform/
├── github.tf          # GitHub secrets/variables configuration
├── iam.tf             # Service accounts and IAM bindings
├── locals.tf          # Local variables from .env file
├── outputs.tf         # Module outputs
├── providers.tf       # Provider configurations
├── services.tf        # Google Cloud API enablement
├── terraform.tf       # Terraform settings
└── variables.tf       # Input variables
```

**Current Resources:**

**One-Time Setup (rarely changes):**
- Service accounts: `{AGENT_NAME}-cicd`, `{AGENT_NAME}-app`
- Workload Identity Federation pool and provider
- IAM role bindings for service accounts
- GitHub Actions secrets: `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`
- GitHub Actions variables: Project/location/bucket configuration
- Google Cloud APIs: aiplatform, iam, discoveryengine, etc.

**Per-Deployment (currently manual):**
- Agent Engine instance (created via Python deployment script, not Terraform)
- Runtime environment variables (passed via GitHub variables)
- Agent-specific configuration

### Current Limitations

1. **Mixed Lifecycle Management**: Setup and deployment resources share the same state file
2. **Risky Operations**: Running `terraform destroy` removes ALL infrastructure, including CI/CD setup
3. **No Infrastructure-as-Code for Deployments**: Agent Engine instances are created imperatively via Python scripts
4. **Manual State Management**: AGENT_ENGINE_ID must be manually captured and added to .env after first deployment
5. **Single Environment**: Cannot easily manage multiple environments (dev/staging/prod)

### Current Workflow Pain Points

From the CI/CD documentation (`docs/cicd_setup_github_actions.md`):

**Phase 2 Manual Step (Required after first deployment):**
> "After your first deployment succeeds, add the deployed Agent Engine ID to the `AGENT_ENGINE_ID` variable in your configuration to enable updates to that instance. **The deployment script ALWAYS creates a new instance when the `AGENT_ENGINE_ID` variable is not set.**"

This indicates the deployment script (`src/deployment/deploy_agent.py`) uses conditional logic:
- `AGENT_ENGINE_ID` not set → Create new Agent Engine instance
- `AGENT_ENGINE_ID` set → Update existing Agent Engine instance

**Problem:** Agent Engine instance lifecycle is managed imperatively in Python, not declaratively in Terraform.

---

## Terraform Workspace Strategies

### Option 1: Terraform Workspaces (NOT Recommended)

**What are workspaces?**
Terraform workspaces provide a way to manage multiple instances of a single configuration's state using the same code.

**Example:**
```bash
terraform workspace new dev
terraform workspace new staging
terraform workspace new prod
terraform workspace select dev
terraform apply
```

**When to use workspaces:**
- Managing identical infrastructure in multiple environments (dev/staging/prod)
- All environments have the same resource types and configuration structure
- Simple environment separation without code duplication

**Why NOT recommended for this use case:**

1. **Same Lifecycle Assumption**: Workspaces assume all resources have the same lifecycle
   - Setup resources (WIF, service accounts) are one-time provisioning
   - Deployment resources (Agent Engine instances) are frequently created/updated/destroyed

2. **No Separation of Concerns**: Both setup and deployment resources would exist in all workspaces
   - Creating a "dev" workspace would try to create dev-specific GitHub secrets (nonsensical)
   - Creating a "deployment" workspace for Agent Engine would still include WIF setup (unnecessary duplication)

3. **Limited Remote State Sharing**: Workspaces use the same backend with different state files
   - Cannot selectively share outputs between different workspace types
   - No way to reference "setup" workspace outputs in "deployment" workspace

4. **Hashicorp's Official Guidance** (from Terraform documentation):
   > "In particular, organizations commonly want to create a strong separation between multiple deployments of the same infrastructure serving different development stages or different internal teams. In this case, the backend used for each deployment often has different credentials and access controls. Workspaces are not a suitable solution in this case."

**Verdict:** Workspaces are designed for managing multiple instances of IDENTICAL infrastructure, not for separating infrastructure with DIFFERENT lifecycles and purposes.

### Option 2: Separate Root Modules (RECOMMENDED)

**What are separate root modules?**
Independent Terraform configurations with their own state files, providers, and resource definitions.

**Example structure:**
```
terraform/
├── setup/          # One-time CI/CD infrastructure
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── backend.tf
└── deployment/     # Per-deployment Agent Engine resources
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── backend.tf
```

**Why this is recommended:**

1. **Clear Separation of Concerns**
   - Setup module: Provisions CI/CD foundation (WIF, service accounts, GitHub integration)
   - Deployment module: Manages Agent Engine instances and versioned resources

2. **Independent Lifecycles**
   - Setup: Apply once, rarely update, never destroy accidentally
   - Deployment: Apply/update/destroy frequently as part of CI/CD pipeline

3. **Selective State Sharing**
   - Deployment module reads setup outputs via `terraform_remote_state`
   - One-way dependency: Deployment depends on setup, but not vice versa

4. **Environment Scalability**
   - Single setup module for all environments
   - Multiple deployment modules (dev/staging/prod) referencing the same setup

5. **Terraform Best Practice** (aligns with official guidance for managing infrastructure at different lifecycles)

**Verdict:** Separate root modules provide the flexibility, safety, and clarity needed for this use case.

---

## Recommended Directory Structure

### High-Level Organization

```
agent-engine-cicd-base/
├── terraform/
│   ├── setup/              # One-time CI/CD infrastructure (setup once, rarely change)
│   │   ├── main.tf         # WIF, service accounts, IAM, GitHub config
│   │   ├── variables.tf    # Input variables (project_id, repo_name, etc.)
│   │   ├── outputs.tf      # Exported values for deployment module
│   │   ├── backend.tf      # Remote state backend configuration
│   │   ├── providers.tf    # Provider configurations
│   │   ├── locals.tf       # Local variables and .env integration
│   │   ├── github.tf       # GitHub secrets/variables resources
│   │   ├── iam.tf          # Service accounts and IAM bindings
│   │   ├── services.tf     # Google Cloud API enablement
│   │   └── README.md       # Setup module documentation
│   │
│   └── deployment/         # Per-deployment Agent Engine resources
│       ├── main.tf         # Agent Engine instance and related resources
│       ├── variables.tf    # Input variables (agent_name, display_name, etc.)
│       ├── outputs.tf      # Exported values (agent_engine_id, resource_name)
│       ├── backend.tf      # Remote state backend configuration
│       ├── providers.tf    # Provider configurations
│       ├── data.tf         # Data sources (including terraform_remote_state)
│       └── README.md       # Deployment module documentation
│
├── .env.example            # Environment variable template
├── .env                    # Local environment variables (gitignored)
└── .github/
    └── workflows/
        └── deploy-to-agent-engine.yaml  # GitHub Actions workflow
```

### Module Responsibilities

#### Setup Module (`terraform/setup/`)

**Purpose:** Provision foundational CI/CD infrastructure that enables GitHub Actions to deploy agents.

**Resources:**
- Google Cloud APIs (aiplatform, iam, discoveryengine, etc.)
- Service Accounts:
  - `{AGENT_NAME}-cicd`: Used by GitHub Actions for deployment operations
  - `{AGENT_NAME}-app`: Used by deployed Agent Engine instances at runtime
- IAM Role Bindings: Grants necessary permissions to service accounts
- Workload Identity Federation:
  - Workload Identity Pool for GitHub Actions
  - OIDC Provider configured to trust the specific GitHub repository
  - IAM binding allowing GitHub to impersonate the CI/CD service account
- GitHub Repository Configuration:
  - Secrets: `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`
  - Variables: Base configuration shared across all deployments

**Outputs (consumed by deployment module):**
```hcl
output "project_id" {
  description = "Google Cloud project ID"
  value       = local.project_id
}

output "location" {
  description = "Google Cloud location for resources"
  value       = var.location  # or from .env
}

output "app_service_account_email" {
  description = "Email of the service account for Agent Engine runtime"
  value       = google_service_account.app.email
}

output "cicd_service_account_email" {
  description = "Email of the service account for GitHub Actions"
  value       = google_service_account.cicd.email
}

output "workload_identity_provider_name" {
  description = "Full resource name of the WIF provider"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "staging_bucket" {
  description = "GCS bucket for Agent Engine staging"
  value       = var.staging_bucket  # or from .env
}
```

**Typical Operations:**
```bash
# Initial provisioning (run once)
cd terraform/setup
terraform init
terraform plan
terraform apply

# Update configuration (rare - e.g., adding new GitHub variables)
terraform apply

# View current state
terraform show
terraform output

# NEVER run terraform destroy unless decommissioning the entire project
```

#### Deployment Module (`terraform/deployment/`)

**Purpose:** Manage Agent Engine instances and deployment-specific resources with full infrastructure-as-code.

**Resources:**
- Vertex AI Agent Engine Instance (`google_vertex_ai_reasoning_engine`)
- Agent-specific IAM bindings (if needed beyond base setup)
- Deployment-specific storage resources (if needed)
- Agentspace registration (optional, potentially via null_resource with local-exec)

**Data Sources:**
```hcl
# Reference setup module outputs
data "terraform_remote_state" "setup" {
  backend = "gcs"

  config = {
    bucket = var.state_bucket
    prefix = "setup"
  }
}

# Use setup outputs
locals {
  project_id            = data.terraform_remote_state.setup.outputs.project_id
  location              = data.terraform_remote_state.setup.outputs.location
  service_account_email = data.terraform_remote_state.setup.outputs.app_service_account_email
  staging_bucket        = data.terraform_remote_state.setup.outputs.staging_bucket
}
```

**Outputs (for external use and monitoring):**
```hcl
output "agent_engine_id" {
  description = "Numeric ID of the deployed Agent Engine instance"
  value       = google_vertex_ai_reasoning_engine.agent.id
}

output "agent_engine_resource_name" {
  description = "Full resource name of the Agent Engine instance"
  value       = google_vertex_ai_reasoning_engine.agent.name
}

output "agent_display_name" {
  description = "Display name of the deployed agent"
  value       = google_vertex_ai_reasoning_engine.agent.display_name
}
```

**Typical Operations:**
```bash
# Deploy new agent instance (automated in CI/CD)
cd terraform/deployment
terraform init
terraform plan
terraform apply

# Update existing agent (automated in CI/CD)
terraform apply

# Destroy agent instance (safe - doesn't affect setup)
terraform destroy

# View deployment state
terraform show
terraform output agent_engine_id
```

---

## Remote State Backend Configuration

### Why Remote State?

**Current setup uses local state** (`terraform.tfstate` file):
- Stored on developer's machine
- Not shared across team members
- No concurrent access protection
- No versioning or backup
- **Critical issue:** GitHub Actions runners start fresh each time, so local state is lost

**Remote state solves these problems:**
- Centralized storage accessible to all team members and CI/CD
- State locking prevents concurrent modifications
- Versioning and backup for disaster recovery
- Secure access control via IAM
- Enables state sharing between modules via `terraform_remote_state`

### Recommended Backend: Google Cloud Storage

**Why GCS for this project:**
- Already using Google Cloud Platform
- Integrates with existing IAM and service accounts
- Supports state locking via native GCS object versioning
- Cost-effective for Terraform state files (minimal storage)
- High availability and durability

**Alternative backends (not recommended for this use case):**
- **Terraform Cloud/Enterprise**: Adds complexity, requires additional account, overkill for single-team project
- **Amazon S3**: Requires multi-cloud setup, adds AWS credentials management
- **Azure Blob Storage**: Requires multi-cloud setup, adds Azure credentials management
- **Local Backend**: Unacceptable for CI/CD (state not persisted across workflow runs)

### GCS Backend Configuration

#### Create State Storage Bucket (One-Time Setup)

**Option 1: Manual creation (recommended for initial setup):**
```bash
# Create a dedicated bucket for Terraform state
export PROJECT_ID="your-project-id"
export STATE_BUCKET="${PROJECT_ID}-terraform-state"

# Create bucket with versioning and security
gcloud storage buckets create gs://${STATE_BUCKET} \
  --project=${PROJECT_ID} \
  --location=US \
  --uniform-bucket-level-access \
  --public-access-prevention

# Enable versioning for state file backup and recovery
gcloud storage buckets update gs://${STATE_BUCKET} --versioning

# Set lifecycle policy to retain old versions for 30 days
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "daysSinceNoncurrentTime": 30,
          "numNewerVersions": 10
        }
      }
    ]
  }
}
EOF

gcloud storage buckets update gs://${STATE_BUCKET} --lifecycle-file=lifecycle.json
```

**Option 2: Terraform-managed (bootstrap problem - need somewhere to store the bucket's state):**
Not recommended for the state bucket itself. Use manual creation or a separate bootstrap configuration.

#### Setup Module Backend Configuration

**`terraform/setup/backend.tf`:**
```hcl
terraform {
  backend "gcs" {
    bucket = "your-project-id-terraform-state"  # Created above
    prefix = "setup"                             # Unique path for setup state

    # Optional: Enable state locking
    # GCS uses object metadata for locking by default when versioning is enabled
  }
}
```

**Initialization:**
```bash
cd terraform/setup
terraform init -backend-config="bucket=${STATE_BUCKET}"

# Or use a backend config file
cat > backend.hcl <<EOF
bucket = "your-project-id-terraform-state"
prefix = "setup"
EOF

terraform init -backend-config=backend.hcl
```

#### Deployment Module Backend Configuration

**`terraform/deployment/backend.tf`:**
```hcl
terraform {
  backend "gcs" {
    bucket = "your-project-id-terraform-state"  # Same bucket as setup
    prefix = "deployment"                        # Different path for deployment state
  }
}
```

**For multiple environments (future enhancement):**
```hcl
# terraform/deployment/backend.tf
terraform {
  backend "gcs" {
    bucket = "your-project-id-terraform-state"
    prefix = "deployment/dev"  # or staging, prod
  }
}
```

### State File Organization in GCS

```
gs://your-project-id-terraform-state/
├── setup/
│   └── default.tfstate           # Setup module state
├── deployment/
│   └── default.tfstate           # Deployment module state
├── deployment-dev/               # (Future) Dev environment
│   └── default.tfstate
├── deployment-staging/           # (Future) Staging environment
│   └── default.tfstate
└── deployment-prod/              # (Future) Production environment
    └── default.tfstate
```

### IAM Permissions for State Access

**Setup Module (manual/developer access):**
```bash
# Grant developers access to setup state
gcloud storage buckets add-iam-policy-binding gs://${STATE_BUCKET} \
  --member="user:developer@example.com" \
  --role="roles/storage.objectAdmin"
```

**Deployment Module (CI/CD service account):**
```hcl
# In terraform/setup/iam.tf - add to cicd_iam_roles list
locals {
  cicd_iam_roles = [
    "roles/aiplatform.user",
    "roles/discoveryengine.editor",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/storage.admin",  # Already included - allows state access
  ]
}
```

The `roles/storage.admin` role already assigned to the CI/CD service account provides sufficient permissions for state file read/write.

### State Locking

**GCS native locking:**
- Terraform automatically uses GCS object metadata for state locking when versioning is enabled
- No additional configuration required
- Prevents concurrent `terraform apply` operations
- Lock is released automatically on completion or error

**Lock behavior:**
```bash
# First terraform apply acquires lock
terraform apply
# Lock acquired: gs://bucket/prefix/default.tflock

# Second concurrent apply waits or fails
terraform apply
# Error: state locked by another process
```

**Force unlock (use with caution):**
```bash
# Only if lock is stuck due to crashed process
terraform force-unlock <LOCK_ID>
```

### State Migration from Local to Remote

**Current state:** Local `terraform.tfstate` file in `terraform/` directory

**Migration steps:**

1. **Backup existing state:**
```bash
cd terraform
cp terraform.tfstate terraform.tfstate.backup
```

2. **Create state bucket:**
```bash
# As shown in "Create State Storage Bucket" section above
```

3. **Add backend configuration:**
```bash
# Create terraform/setup/backend.tf with GCS backend config
```

4. **Initialize with migration:**
```bash
cd terraform/setup
terraform init -migrate-state

# Terraform will prompt: "Do you want to copy existing state to the new backend?"
# Answer: yes
```

5. **Verify migration:**
```bash
# Confirm state is in GCS
gcloud storage ls gs://${STATE_BUCKET}/setup/

# Verify local state is now just a reference
cat .terraform/terraform.tfstate
```

6. **Clean up local state (after verification):**
```bash
# Remove local state file (ONLY after confirming remote state works)
rm terraform.tfstate terraform.tfstate.backup
```

---

## State Data Sharing Between Modules

### The `terraform_remote_state` Data Source

**Purpose:** Allow the deployment module to read outputs from the setup module without duplicating resource definitions.

**How it works:**
1. Setup module defines outputs
2. Deployment module declares `terraform_remote_state` data source pointing to setup state
3. Deployment module references setup outputs via `data.terraform_remote_state.setup.outputs.*`

### Setup Module Outputs

**`terraform/setup/outputs.tf`:**
```hcl
# Core project configuration
output "project_id" {
  description = "Google Cloud project ID"
  value       = local.project_id
  sensitive   = false
}

output "location" {
  description = "Google Cloud location for Vertex AI resources"
  value       = local.location  # From .env or variable
  sensitive   = false
}

# Service accounts
output "app_service_account_email" {
  description = "Email of the service account for Agent Engine runtime"
  value       = google_service_account.app.email
  sensitive   = false
}

output "cicd_service_account_email" {
  description = "Email of the CI/CD service account used by GitHub Actions"
  value       = google_service_account.cicd.email
  sensitive   = false
}

# Workload Identity Federation
output "workload_identity_provider_name" {
  description = "Full resource name of the Workload Identity Pool provider"
  value       = google_iam_workload_identity_pool_provider.github.name
  sensitive   = false
}

# Storage configuration
output "staging_bucket" {
  description = "GCS bucket name for Agent Engine staging (without gs:// prefix)"
  value       = local.staging_bucket  # From .env or variable
  sensitive   = false
}

output "gcs_dir_name" {
  description = "Directory name within staging bucket for agent files"
  value       = local.gcs_dir_name  # From .env or variable
  sensitive   = false
}

# GitHub repository
output "repository_full_name" {
  description = "Full GitHub repository name (owner/repo)"
  value       = "${local.repository_owner}/${local.repository_name}"
  sensitive   = false
}

# Agent configuration
output "agent_name" {
  description = "Agent name used for resource naming"
  value       = local.agent_name
  sensitive   = false
}

# Enabled APIs (for debugging)
output "enabled_services" {
  description = "List of enabled Google Cloud services"
  value       = [for service in google_project_service.main : service.service]
  sensitive   = false
}
```

**Key principles:**
- Export ALL values that deployment module might need
- Use descriptive names that clearly indicate purpose
- Mark sensitive values appropriately (none in this case, but good practice)
- Include documentation via `description` field

### Deployment Module Data Source

**`terraform/deployment/data.tf`:**
```hcl
# Read setup module state to get infrastructure values
data "terraform_remote_state" "setup" {
  backend = "gcs"

  config = {
    bucket = var.state_bucket  # Pass via variable or .env
    prefix = "setup"           # Must match setup module backend prefix
  }
}

# Optional: Read .env for deployment-specific overrides
data "dotenv" "config" {
  filename = "${path.module}/../../.env"
}

# Local values combining setup outputs and deployment inputs
locals {
  # From setup module (shared infrastructure)
  project_id            = data.terraform_remote_state.setup.outputs.project_id
  location              = data.terraform_remote_state.setup.outputs.location
  service_account_email = data.terraform_remote_state.setup.outputs.app_service_account_email
  staging_bucket        = data.terraform_remote_state.setup.outputs.staging_bucket
  gcs_dir_name          = data.terraform_remote_state.setup.outputs.gcs_dir_name

  # From deployment inputs (deployment-specific)
  agent_display_name = coalesce(var.agent_display_name, data.dotenv.config.entries.AGENT_DISPLAY_NAME, "ADK Agent")
  agent_description  = coalesce(var.agent_description, data.dotenv.config.entries.AGENT_DESCRIPTION, "ADK Agent")

  # Deployment-specific environment variables for Agent Engine runtime
  agent_env_vars = {
    AGENT_NAME                                     = data.terraform_remote_state.setup.outputs.agent_name
    LOG_LEVEL                                      = var.log_level
    OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT = var.otel_capture_message_content
  }
}
```

**`terraform/deployment/variables.tf`:**
```hcl
variable "state_bucket" {
  description = "GCS bucket name for Terraform remote state (without gs:// prefix)"
  type        = string
}

variable "agent_display_name" {
  description = "Display name for the Agent Engine instance"
  type        = string
  default     = null
}

variable "agent_description" {
  description = "Description for the Agent Engine instance"
  type        = string
  default     = null
}

variable "log_level" {
  description = "Logging level for the agent (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
  type        = string
  default     = "INFO"
}

variable "otel_capture_message_content" {
  description = "Enable capturing message content in OpenTelemetry traces"
  type        = string
  default     = "true"
}

variable "wheel_file_path" {
  description = "Path to the wheel file for agent deployment"
  type        = string
}
```

### Using Shared Data in Deployment Resources

**`terraform/deployment/main.tf`:**
```hcl
# Note: This is a conceptual example
# The actual Vertex AI Agent Engine Terraform resource may not exist yet
# This demonstrates how you WOULD use it when available

resource "google_vertex_ai_reasoning_engine" "agent" {
  project      = local.project_id
  location     = local.location
  display_name = local.agent_display_name
  description  = local.agent_description

  # Use service account from setup module
  service_account = local.service_account_email

  # Use staging bucket from setup module
  staging_bucket = "gs://${local.staging_bucket}"
  gcs_dir_name   = local.gcs_dir_name

  # Deployment-specific configuration
  runtime_config {
    environment_variables = local.agent_env_vars
  }

  # Wheel file and dependencies
  requirements     = [basename(var.wheel_file_path)]
  extra_packages   = [basename(var.wheel_file_path)]

  # Enable tracing
  enable_tracing = true
}

# Alternative: Use null_resource to call Python deployment script
# This is the CURRENT approach until native Terraform resource exists
resource "null_resource" "deploy_agent" {
  triggers = {
    # Redeploy when wheel file changes
    wheel_file_checksum = filemd5(var.wheel_file_path)

    # Or use timestamp for always deploy
    timestamp = timestamp()
  }

  provisioner "local-exec" {
    command = "uv run deploy"

    environment = {
      GOOGLE_CLOUD_PROJECT        = local.project_id
      GOOGLE_CLOUD_LOCATION       = local.location
      GOOGLE_CLOUD_STORAGE_BUCKET = local.staging_bucket
      GCS_DIR_NAME                = local.gcs_dir_name
      AGENT_NAME                  = data.terraform_remote_state.setup.outputs.agent_name
      AGENT_DISPLAY_NAME          = local.agent_display_name
      AGENT_DESCRIPTION           = local.agent_description
      LOG_LEVEL                   = var.log_level
      OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT = var.otel_capture_message_content
      # Note: AGENT_ENGINE_ID is captured from previous deployment outputs
      # Would need to handle this via state management
    }
  }
}
```

### Handling Agent Engine ID for Updates

**Current challenge:** The Python deployment script requires `AGENT_ENGINE_ID` to update existing instances, but this value is only known AFTER the first deployment.

**Solution with Terraform:**

**Option 1: Terraform-managed resource (ideal, when available):**
```hcl
# Terraform automatically tracks resource IDs in state
resource "google_vertex_ai_reasoning_engine" "agent" {
  # Configuration...
}

output "agent_engine_id" {
  value = google_vertex_ai_reasoning_engine.agent.id
}

# Updates handled automatically by terraform apply
# No manual AGENT_ENGINE_ID management needed
```

**Option 2: null_resource with state capture (current workaround):**
```hcl
resource "null_resource" "deploy_agent" {
  provisioner "local-exec" {
    command = <<-EOT
      # Deploy and capture AGENT_ENGINE_ID
      AGENT_ENGINE_ID=$(terraform output -state=${path.module}/terraform.tfstate agent_engine_id 2>/dev/null || echo "")
      export AGENT_ENGINE_ID
      uv run deploy | tee /tmp/deploy_output.txt

      # Extract AGENT_ENGINE_ID from deployment output
      AGENT_ENGINE_ID=$(grep -oP 'reasoningEngines/\K[0-9]+' /tmp/deploy_output.txt | tail -1)

      # Save to Terraform output for next run
      echo "{\"agent_engine_id\": {\"value\": \"$AGENT_ENGINE_ID\"}}" > ${path.module}/agent_engine_id.json
    EOT

    environment = {
      # Environment variables as before...
    }
  }
}

data "local_file" "agent_engine_id" {
  depends_on = [null_resource.deploy_agent]
  filename   = "${path.module}/agent_engine_id.json"
}

locals {
  agent_engine_id = try(jsondecode(data.local_file.agent_engine_id.content).agent_engine_id.value, "")
}

output "agent_engine_id" {
  description = "ID of the deployed Agent Engine instance"
  value       = local.agent_engine_id
}
```

**Option 3: External data source (cleaner workaround):**
```hcl
data "external" "current_agent" {
  program = ["bash", "-c", <<-EOT
    # Query for existing agent by name
    AGENT_ID=$(gcloud ai reasoning-engines list \
      --project=${local.project_id} \
      --location=${local.location} \
      --filter="displayName:${local.agent_display_name}" \
      --format="value(name)" \
      --limit=1 | grep -oP 'reasoningEngines/\K[0-9]+' || echo "")

    echo "{\"agent_engine_id\": \"$AGENT_ID\"}"
  EOT
  ]
}

resource "null_resource" "deploy_agent" {
  provisioner "local-exec" {
    command = "uv run deploy"

    environment = {
      AGENT_ENGINE_ID = data.external.current_agent.result.agent_engine_id
      # Other environment variables...
    }
  }
}
```

---

## GitHub Actions Integration Patterns

### Current Workflow Analysis

**`.github/workflows/deploy-to-agent-engine.yaml`:**
- Triggers on: Push to main, manual dispatch, workflow call
- Path filters: `src/**`, `terraform/**`, `uv.lock`
- Steps: Checkout → Setup Python → Auth to GCP → Install UV → Build wheel → Deploy → Register with Agentspace

**Current deployment approach:**
- Uses Python script (`uv run deploy`) for Agent Engine deployment
- Terraform NOT run in CI/CD pipeline
- Terraform used manually by developers for one-time setup

### Recommended GitHub Actions Workflow

**Goal:** Run deployment Terraform automatically in CI/CD while keeping setup Terraform manual.

#### Updated Workflow Structure

**`.github/workflows/deploy-to-agent-engine.yaml`:**
```yaml
name: Deploy to Agent Engine

on:
  workflow_dispatch:
  workflow_call:
  push:
    branches:
      - main
    paths:
      - "src/**"
      - "terraform/deployment/**"  # Trigger on deployment Terraform changes
      - "uv.lock"

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: "read"
      id-token: "write"
    timeout-minutes: 15

    # Working directory for Terraform commands
    defaults:
      run:
        working-directory: terraform/deployment

    steps:
      - name: Checkout code
        uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version-file: "pyproject.toml"

      - name: Authenticate to Google Cloud
        id: auth
        uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}
          create_credentials_file: true
          token_format: "access_token"

      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          version: "0.8.21"

      - name: Install project dependencies
        working-directory: .  # Root directory for uv
        run: uv sync --frozen

      - name: Build wheel package
        working-directory: .  # Root directory for uv build
        run: uv build --wheel --out-dir .

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.x"  # Or specify exact version

      - name: Terraform Init
        run: terraform init
        env:
          # Authenticate Terraform to GCS backend using GOOGLE_APPLICATION_CREDENTIALS
          # (set by google-github-actions/auth step)
          TF_VAR_state_bucket: ${{ vars.TERRAFORM_STATE_BUCKET }}

      - name: Terraform Plan
        run: terraform plan -out=tfplan
        env:
          TF_VAR_state_bucket: ${{ vars.TERRAFORM_STATE_BUCKET }}
          TF_VAR_agent_display_name: ${{ vars.AGENT_DISPLAY_NAME }}
          TF_VAR_agent_description: ${{ vars.AGENT_DESCRIPTION }}
          TF_VAR_log_level: ${{ vars.LOG_LEVEL }}
          TF_VAR_otel_capture_message_content: ${{ vars.OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT }}
          TF_VAR_wheel_file_path: "../../$(ls ../../*.whl)"

      - name: Terraform Apply
        run: terraform apply -auto-approve tfplan

      - name: Capture Deployment Outputs
        id: deployment
        run: |
          echo "agent_engine_id=$(terraform output -raw agent_engine_id)" >> $GITHUB_OUTPUT
          echo "agent_resource_name=$(terraform output -raw agent_engine_resource_name)" >> $GITHUB_OUTPUT

      - name: Register with Agentspace
        if: ${{ vars.AGENTSPACE_APP_ID != '' && vars.AGENTSPACE_APP_LOCATION != '' }}
        working-directory: .  # Root directory for uv run
        run: uv run register
        env:
          PYTHONUNBUFFERED: "1"
          GOOGLE_GENAI_USE_VERTEXAI: ${{ vars.GOOGLE_GENAI_USE_VERTEXAI }}
          GOOGLE_CLOUD_PROJECT: ${{ vars.GOOGLE_CLOUD_PROJECT }}
          GOOGLE_CLOUD_LOCATION: ${{ vars.GOOGLE_CLOUD_LOCATION }}
          AGENT_DISPLAY_NAME: ${{ vars.AGENT_DISPLAY_NAME }}
          AGENT_DESCRIPTION: ${{ vars.AGENT_DESCRIPTION }}
          AGENT_ENGINE_ID: ${{ steps.deployment.outputs.agent_engine_id }}
          AGENTSPACE_APP_ID: ${{ vars.AGENTSPACE_APP_ID }}
          AGENTSPACE_APP_LOCATION: ${{ vars.AGENTSPACE_APP_LOCATION }}
          GCP_ACCESS_TOKEN: ${{ steps.auth.outputs.access_token }}

      - name: Deployment Summary
        run: |
          echo "## Deployment Complete ✅" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **Agent Engine ID:** ${{ steps.deployment.outputs.agent_engine_id }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Resource Name:** ${{ steps.deployment.outputs.agent_resource_name }}" >> $GITHUB_STEP_SUMMARY
          echo "- **Display Name:** ${{ vars.AGENT_DISPLAY_NAME }}" >> $GITHUB_STEP_SUMMARY
```

#### Required GitHub Variables

**Setup module manages these (no change):**
- `GCP_WORKLOAD_IDENTITY_PROVIDER` (secret)
- `GCP_SERVICE_ACCOUNT` (secret)
- `GOOGLE_CLOUD_PROJECT` (variable)
- `GOOGLE_CLOUD_LOCATION` (variable)
- `GOOGLE_CLOUD_STORAGE_BUCKET` (variable)

**New variable for deployment module:**
- `TERRAFORM_STATE_BUCKET`: GCS bucket name for remote state (e.g., "my-project-terraform-state")

**Deployment-specific variables (already exist):**
- `AGENT_DISPLAY_NAME`
- `AGENT_DESCRIPTION`
- `LOG_LEVEL`
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`
- `AGENTSPACE_APP_ID` (optional)
- `AGENTSPACE_APP_LOCATION` (optional)

#### Setup Module Workflow (Manual)

**`terraform/setup/README.md` - Manual Operations:**
```markdown
# Setup Module - Manual Operations

## Initial Provisioning

1. Create state storage bucket:
   ```bash
   export PROJECT_ID="your-project-id"
   export STATE_BUCKET="${PROJECT_ID}-terraform-state"
   gcloud storage buckets create gs://${STATE_BUCKET} \
     --project=${PROJECT_ID} \
     --location=US \
     --uniform-bucket-level-access \
     --public-access-prevention
   gcloud storage buckets update gs://${STATE_BUCKET} --versioning
   ```

2. Initialize Terraform with remote backend:
   ```bash
   cd terraform/setup
   terraform init -backend-config="bucket=${STATE_BUCKET}"
   ```

3. Review and apply:
   ```bash
   terraform plan
   terraform apply
   ```

4. Configure GitHub variable for deployment:
   ```bash
   gh variable set TERRAFORM_STATE_BUCKET --body "${STATE_BUCKET}"
   ```

## Updating Setup Configuration

```bash
cd terraform/setup
terraform plan
terraform apply
```

## Viewing Current State

```bash
terraform show
terraform output
```

## ⚠️ NEVER run `terraform destroy` unless decommissioning the entire project
```

### Terraform in CI/CD Best Practices

**1. Use Terraform Plan for PR Reviews:**

Add a separate workflow for PR validation:

**`.github/workflows/terraform-plan.yaml`:**
```yaml
name: Terraform Plan

on:
  pull_request:
    paths:
      - "terraform/deployment/**"
      - "src/**"
      - "uv.lock"

jobs:
  plan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      id-token: write

    steps:
      - uses: actions/checkout@v5

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}
          create_credentials_file: true

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        working-directory: terraform/deployment
        run: terraform init
        env:
          TF_VAR_state_bucket: ${{ vars.TERRAFORM_STATE_BUCKET }}

      - name: Terraform Plan
        working-directory: terraform/deployment
        run: terraform plan -no-color
        env:
          TF_VAR_state_bucket: ${{ vars.TERRAFORM_STATE_BUCKET }}
          TF_VAR_wheel_file_path: "../../dummy.whl"  # Placeholder for planning
        continue-on-error: true

      - name: Comment Plan on PR
        uses: actions/github-script@v7
        with:
          script: |
            const output = `### Terraform Plan
            \`\`\`
            ${{ steps.plan.outputs.stdout }}
            \`\`\`
            `;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            });
```

**2. Terraform Version Pinning:**

**`terraform/deployment/.terraform-version`:**
```
1.9.8
```

**3. State File Security:**

- NEVER commit `terraform.tfstate` files
- Ensure `.gitignore` includes state files
- Use GCS bucket IAM to restrict state access
- Enable versioning for state recovery

**4. Terraform Cloud Alternative (Optional):**

For teams preferring managed Terraform state and collaboration:

**`terraform/deployment/backend.tf`:**
```hcl
terraform {
  cloud {
    organization = "your-org"

    workspaces {
      name = "agent-engine-deployment"
    }
  }
}
```

Requires Terraform Cloud account and `TF_API_TOKEN` secret in GitHub.

---

## Migration Path from Current Setup

### Phase 1: Add Remote State to Existing Setup

**Goal:** Migrate current monolithic Terraform to remote state without restructuring.

**Steps:**

1. **Create state storage bucket** (as shown in Remote State section)

2. **Add backend configuration:**
   ```bash
   cd terraform
   cat > backend.tf <<EOF
   terraform {
     backend "gcs" {
       bucket = "your-project-id-terraform-state"
       prefix = "legacy"
     }
   }
   EOF
   ```

3. **Initialize with migration:**
   ```bash
   terraform init -migrate-state
   # Answer "yes" when prompted to copy state
   ```

4. **Verify migration:**
   ```bash
   gcloud storage ls gs://your-project-id-terraform-state/legacy/
   terraform show
   ```

5. **Update .gitignore:**
   ```bash
   echo "*.tfstate" >> .gitignore
   echo "*.tfstate.backup" >> .gitignore
   git add .gitignore backend.tf
   git commit -m "chore: migrate Terraform state to GCS backend"
   ```

**Status after Phase 1:**
- Remote state enabled ✅
- CI/CD can access state ✅
- Still monolithic configuration (setup + deployment together) ⚠️

### Phase 2: Split into Setup and Deployment Modules

**Goal:** Separate concerns into two root modules.

**Steps:**

1. **Create new directory structure:**
   ```bash
   mkdir -p terraform/setup terraform/deployment
   ```

2. **Move setup resources:**
   ```bash
   cd terraform

   # Files for setup module
   mv github.tf setup/
   mv iam.tf setup/
   mv services.tf setup/

   # Copy shared files
   cp providers.tf setup/
   cp variables.tf setup/
   cp locals.tf setup/

   # Create new files
   touch setup/backend.tf
   touch setup/outputs.tf
   touch setup/README.md
   ```

3. **Create setup backend configuration:**
   ```hcl
   # terraform/setup/backend.tf
   terraform {
     backend "gcs" {
       bucket = "your-project-id-terraform-state"
       prefix = "setup"
     }
   }
   ```

4. **Define setup outputs:**
   ```hcl
   # terraform/setup/outputs.tf
   # (As shown in "Setup Module Outputs" section above)
   ```

5. **Import existing resources into setup module:**
   ```bash
   cd terraform/setup
   terraform init -migrate-state

   # Terraform will detect existing resources and migrate state
   terraform plan  # Should show "no changes" if migration successful
   ```

6. **Create deployment module (initially using null_resource):**
   ```bash
   cd terraform/deployment

   # Create files
   touch main.tf backend.tf variables.tf outputs.tf data.tf providers.tf README.md
   ```

7. **Configure deployment module:**
   ```hcl
   # terraform/deployment/backend.tf
   terraform {
     backend "gcs" {
       bucket = "your-project-id-terraform-state"
       prefix = "deployment"
     }
   }

   # terraform/deployment/data.tf
   data "terraform_remote_state" "setup" {
     backend = "gcs"
     config = {
       bucket = var.state_bucket
       prefix = "setup"
     }
   }

   # terraform/deployment/main.tf
   # (Initial implementation using null_resource to call Python script)
   # (See "Using Shared Data in Deployment Resources" section)
   ```

8. **Initialize deployment module:**
   ```bash
   cd terraform/deployment
   terraform init
   terraform plan
   # Review plan - should create null_resource for deployment
   ```

9. **Test deployment workflow:**
   ```bash
   # Build wheel
   cd ../..
   uv build --wheel --out-dir .

   # Run deployment Terraform
   cd terraform/deployment
   terraform apply
   ```

10. **Update GitHub Actions workflow:**
    ```bash
    # Replace Python deployment step with Terraform steps
    # (As shown in "GitHub Actions Integration Patterns" section)
    ```

11. **Clean up legacy Terraform:**
    ```bash
    cd terraform
    rm -rf .terraform terraform.tfstate* backend.tf
    # Remove individual .tf files now moved to setup/
    ```

**Status after Phase 2:**
- Setup module: Manages CI/CD infrastructure ✅
- Deployment module: Manages Agent Engine instances ✅
- State sharing via terraform_remote_state ✅
- GitHub Actions runs deployment Terraform ✅

### Phase 3: Transition to Native Terraform Resources (Future)

**Goal:** Replace null_resource + Python script with native Terraform resources when available.

**Prerequisites:**
- Vertex AI Agent Engine Terraform resource becomes available (currently doesn't exist in google provider)
- Or use custom provider / Terraform CDK

**Implementation:**

1. **Check for resource availability:**
   ```bash
   terraform providers schema -json | jq '.provider_schemas["registry.terraform.io/hashicorp/google"].resource_schemas' | grep reasoning
   ```

2. **Replace null_resource with native resource:**
   ```hcl
   # terraform/deployment/main.tf
   resource "google_vertex_ai_reasoning_engine" "agent" {
     project      = local.project_id
     location     = local.location
     display_name = local.agent_display_name
     description  = local.agent_description

     service_account = local.service_account_email
     staging_bucket  = "gs://${local.staging_bucket}"

     # ... rest of configuration
   }
   ```

3. **Remove Python deployment script dependency:**
   - Wheel file upload handled by Terraform
   - Environment variables set in resource config
   - AGENT_ENGINE_ID automatically tracked in state

4. **Update GitHub Actions workflow:**
   - Remove `uv run deploy` step
   - Terraform handles complete deployment lifecycle

**Status after Phase 3:**
- Fully declarative infrastructure ✅
- No manual AGENT_ENGINE_ID management ✅
- Terraform manages complete lifecycle ✅

### Migration Timeline

| Phase | Duration | Effort | Impact |
|-------|----------|--------|--------|
| Phase 1: Remote State | 1-2 hours | Low | Low risk, immediate CI/CD benefit |
| Phase 2: Module Split | 4-8 hours | Medium | Moderate risk, testing required |
| Phase 3: Native Resources | TBD | High | Depends on Terraform provider availability |

**Recommendation:** Implement Phase 1 immediately, Phase 2 when ready to refactor, Phase 3 when resources become available.

---

## Trade-offs and Considerations

### Approach Comparison Matrix

| Aspect | Current Monolith | Terraform Workspaces | Separate Root Modules |
|--------|------------------|---------------------|---------------------|
| **Separation of Concerns** | ❌ Mixed | ⚠️ Logical only | ✅ Physical |
| **State Isolation** | ❌ Single file | ⚠️ Same backend | ✅ Separate files |
| **Accidental Destruction Risk** | ❌ High | ⚠️ Medium | ✅ Low |
| **Multi-Environment Support** | ❌ No | ✅ Yes | ✅ Yes |
| **CI/CD Integration** | ⚠️ Manual only | ⚠️ Complex | ✅ Simple |
| **State Sharing** | ✅ N/A (single state) | ❌ Limited | ✅ terraform_remote_state |
| **Learning Curve** | ✅ Low | ⚠️ Medium | ⚠️ Medium |
| **Maintenance Overhead** | ✅ Low | ⚠️ Medium | ⚠️ Medium |
| **Production Readiness** | ❌ No | ⚠️ Acceptable | ✅ Yes |

### Pros and Cons

#### Separate Root Modules (Recommended)

**Pros:**
1. **Clear separation of lifecycles** - Setup rarely changes, deployment changes frequently
2. **Reduced blast radius** - Destroying deployment module doesn't affect CI/CD setup
3. **Independent state files** - Safer concurrent operations, easier debugging
4. **Flexible state sharing** - One-way dependency via terraform_remote_state
5. **Multi-environment scalability** - Easy to add dev/staging/prod deployments
6. **CI/CD friendly** - Deployment module runs in pipeline, setup module manual
7. **Aligns with Terraform best practices** - Recommended for different resource lifecycles

**Cons:**
1. **Increased complexity** - Two modules to maintain instead of one
2. **State management** - Must manage remote state backend
3. **Data passing** - Requires terraform_remote_state understanding
4. **Initial setup time** - More upfront configuration work
5. **Potential for drift** - If setup outputs change, deployment module may need updates

**Mitigation strategies:**
- Comprehensive documentation for both modules
- Clear README files with usage examples
- Automated testing of module integration
- Version pinning for Terraform and providers

#### Terraform Workspaces (Not Recommended for This Use Case)

**Pros:**
1. **Simple environment separation** - Easy to create dev/staging/prod
2. **Shared codebase** - DRY principle, no code duplication
3. **Built-in Terraform feature** - No additional tools required

**Cons:**
1. **Same lifecycle assumption** - All resources managed together
2. **Limited use case** - Designed for identical infrastructure, not different purposes
3. **State backend limitation** - All workspaces in same backend, harder to control access
4. **Workspace proliferation** - Mixing "setup" and "deployment" workspaces is confusing
5. **Not suitable for setup vs deployment separation** - Fundamental mismatch with use case

**Verdict:** Workspaces are the wrong tool for this problem.

#### Current Monolithic Approach (Status Quo)

**Pros:**
1. **Simplicity** - Single Terraform configuration
2. **No state sharing complexity** - Everything in one state
3. **Easy to understand** - Clear for beginners

**Cons:**
1. **High risk of accidental destruction** - terraform destroy removes ALL infrastructure
2. **No CI/CD integration** - Deployment still manual via Python script
3. **Mixed lifecycles** - Setup and deployment resources together
4. **Manual AGENT_ENGINE_ID management** - Error-prone two-phase setup process
5. **Not scalable** - Difficult to add multiple environments

**Verdict:** Acceptable for prototyping, unsuitable for production.

### Decision Framework

**Choose Separate Root Modules if:**
- ✅ You need production-grade infrastructure
- ✅ You want CI/CD-automated deployments
- ✅ You need multiple environments (dev/staging/prod)
- ✅ You want to minimize accidental infrastructure destruction
- ✅ You're comfortable with Terraform best practices

**Stick with Current Monolith if:**
- ✅ You're still in early prototyping phase
- ✅ You only deploy manually
- ✅ You have a single environment
- ✅ You're willing to accept higher risk for simplicity
- ❌ You need CI/CD automation (then you must switch)

### Cost Considerations

**GCS State Backend:**
- Storage: ~$0.02/GB/month (state files are tiny, typically < 1MB)
- Operations: ~$0.004 per 10,000 operations
- **Total cost: < $1/month for typical usage**

**Terraform Cloud Alternative:**
- Free tier: Up to 5 users, 500 resource limit
- Team tier: $20/user/month
- **Recommendation:** Use GCS for cost efficiency

**CI/CD Compute:**
- GitHub Actions: 2,000 free minutes/month for private repos
- Additional minutes: $0.008/minute
- **Recommendation:** Optimize workflow to minimize runtime

---

## Implementation Checklist

### Setup Module Implementation

- [ ] Create `terraform/setup/` directory structure
- [ ] Move setup resources (iam.tf, github.tf, services.tf)
- [ ] Create `backend.tf` with GCS configuration
- [ ] Define comprehensive `outputs.tf` for state sharing
- [ ] Update `providers.tf` for setup module context
- [ ] Write `README.md` with manual operation instructions
- [ ] Initialize Terraform and migrate state
- [ ] Verify setup module: `terraform plan` shows no changes
- [ ] Test state backend: Confirm state in GCS bucket

### Deployment Module Implementation

- [ ] Create `terraform/deployment/` directory structure
- [ ] Create `backend.tf` with separate GCS prefix
- [ ] Define `data.tf` with terraform_remote_state reference
- [ ] Create `variables.tf` for deployment inputs
- [ ] Implement `main.tf` with deployment resources
  - [ ] Option A: null_resource calling Python script (immediate)
  - [ ] Option B: Native Terraform resource (when available)
- [ ] Define `outputs.tf` for agent_engine_id and resource_name
- [ ] Write `README.md` with usage examples
- [ ] Initialize Terraform: `terraform init`
- [ ] Test deployment: `terraform plan` and `terraform apply`
- [ ] Verify state sharing: Check data.terraform_remote_state.setup.outputs

### GitHub Actions Integration

- [ ] Add `TERRAFORM_STATE_BUCKET` to GitHub variables
- [ ] Update `.github/workflows/deploy-to-agent-engine.yaml`
  - [ ] Add Terraform setup step
  - [ ] Add Terraform init/plan/apply steps
  - [ ] Capture deployment outputs
  - [ ] Pass agent_engine_id to Agentspace registration
- [ ] Create `.github/workflows/terraform-plan.yaml` for PR reviews
- [ ] Test workflow with dummy deployment
- [ ] Verify Terraform outputs in GitHub Actions logs

### Documentation Updates

- [ ] Update `README.md` quickstart with Terraform module info
- [ ] Update `docs/cicd_setup_github_actions.md`
  - [ ] Document two-module architecture
  - [ ] Update Phase 1: Setup module provisioning
  - [ ] Remove Phase 2: No more manual AGENT_ENGINE_ID capture
  - [ ] Update Phase 3: Terraform-managed deployments
- [ ] Update `CLAUDE.md` with Terraform commands for both modules
- [ ] Create `terraform/setup/README.md` with manual operations
- [ ] Create `terraform/deployment/README.md` with CI/CD usage

### Testing and Validation

- [ ] Test setup module: Apply and verify outputs
- [ ] Test deployment module: Deploy agent successfully
- [ ] Test state sharing: Confirm deployment reads setup outputs
- [ ] Test GitHub Actions: End-to-end pipeline run
- [ ] Test update workflow: Modify agent and redeploy
- [ ] Test multiple deployments: Create dev/staging if applicable
- [ ] Test disaster recovery: Restore state from GCS versions

### Rollout Plan

**Week 1: Phase 1 - Remote State**
- Day 1-2: Create state bucket and migrate current setup
- Day 3-4: Test remote state with manual operations
- Day 5: Update documentation

**Week 2: Phase 2 - Module Separation**
- Day 1-2: Create setup module and migrate resources
- Day 3-4: Create deployment module with null_resource
- Day 5: Test both modules independently and together

**Week 3: Phase 3 - CI/CD Integration**
- Day 1-2: Update GitHub Actions workflow
- Day 3-4: Test automated deployments
- Day 5: Final documentation and team training

**Future: Phase 4 - Native Resources**
- Monitor Terraform google provider for reasoning_engine resource
- Plan migration from null_resource to native resource
- Implement and test when available

---

## References and Best Practices

### Official Terraform Documentation

**Core Concepts:**
- [Terraform Workspaces](https://developer.hashicorp.com/terraform/language/state/workspaces) - When and when not to use workspaces
- [Remote State](https://developer.hashicorp.com/terraform/language/state/remote) - Backend configuration and management
- [Remote State Data Source](https://developer.hashicorp.com/terraform/language/state/remote-state-data) - Sharing data between configurations
- [Organizing Configuration](https://developer.hashicorp.com/terraform/tutorials/modules/organize-configuration) - Best practices for structure

**Backend Configuration:**
- [GCS Backend](https://developer.hashicorp.com/terraform/language/backends/gcs) - Google Cloud Storage backend reference
- [Backend Configuration](https://developer.hashicorp.com/terraform/language/backend) - General backend concepts
- [State Locking](https://developer.hashicorp.com/terraform/language/state/locking) - Preventing concurrent modifications

**Advanced Topics:**
- [Terraform Modules](https://developer.hashicorp.com/terraform/language/modules) - Reusable configuration components
- [Data Sources](https://developer.hashicorp.com/terraform/language/data-sources) - Reading external data
- [Outputs](https://developer.hashicorp.com/terraform/language/values/outputs) - Exporting values from modules

### Google Cloud Documentation

**Workload Identity Federation:**
- [Workload Identity Federation with GitHub Actions](https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines#github-actions_1)
- [Configure Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [Best Practices for WIF](https://cloud.google.com/iam/docs/best-practices-for-using-workload-identity-federation)

**Service Accounts:**
- [Service Account Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
- [Understanding Service Accounts](https://cloud.google.com/iam/docs/service-account-overview)

**Cloud Storage:**
- [Creating Buckets](https://cloud.google.com/storage/docs/creating-buckets)
- [Bucket Locations](https://cloud.google.com/storage/docs/locations)
- [Object Versioning](https://cloud.google.com/storage/docs/object-versioning)

**Vertex AI:**
- [Deploy an Agent](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy)
- [Agent Engine Overview](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview)

### GitHub Actions

**Official Actions:**
- [google-github-actions/auth](https://github.com/google-github-actions/auth) - Authenticate to Google Cloud
- [hashicorp/setup-terraform](https://github.com/hashicorp/setup-terraform) - Install Terraform in workflows
- [actions/github-script](https://github.com/actions/github-script) - Run custom scripts in workflows

**Best Practices:**
- [Using Variables](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables)
- [Using Secrets](https://docs.github.com/en/actions/security-for-github-actions/using-secrets-in-github-actions)
- [Workflow Security](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)

### Community Resources and Real-World Examples

**Terraform State Management:**
- [Gruntwork: How to Manage Terraform State](https://blog.gruntwork.io/how-to-manage-terraform-state-28f5697e68fa)
- [Terragrunt](https://terragrunt.gruntwork.io/) - Tool for managing multiple Terraform modules
- [Atlantis](https://www.runatlantis.io/) - Terraform pull request automation

**Multi-Environment Patterns:**
- [Terraform Best Practices](https://www.terraform-best-practices.com/) - Community-maintained guide
- [Google Cloud Foundation Toolkit](https://cloud.google.com/foundation-toolkit) - Reference architectures
- [Terraform Google Examples](https://github.com/terraform-google-modules) - Official Google Cloud Terraform modules

**CI/CD Integration:**
- [Terraform in CI/CD](https://developer.hashicorp.com/terraform/tutorials/automation/github-actions) - Official HashiCorp tutorial
- [GitOps with Terraform](https://www.gitops.tech/#terraform) - GitOps principles applied to Terraform
- [Terraform Automation Best Practices](https://developer.hashicorp.com/terraform/cloud-docs/recommended-practices/automation)

### Key Takeaways from HashiCorp Guidance

**When to use workspaces (from official docs):**
> "Workspaces in the Terraform CLI are separate instances of state data inside the same Terraform working directory. They are convenience features for using one configuration to manage multiple similar groups of resources."

**When NOT to use workspaces (from official docs):**
> "Organizations commonly want to create a strong separation between multiple deployments of the same infrastructure serving different development stages or different internal teams. In this case, the backend used for each deployment often has different credentials and access controls. **Workspaces are not a suitable solution in this case.**"

**On organizing configurations:**
> "Organize infrastructure into multiple Terraform configurations based on the rate of change, blast radius, and administrative scope."

**This aligns perfectly with separating setup (rare changes, high blast radius) from deployment (frequent changes, limited blast radius).**

### Terraform Provider Resources

**Current Status:**
- Google Cloud Terraform Provider: v7.6.0 (as of research date)
- Vertex AI Reasoning Engine resource: **NOT YET AVAILABLE** in official provider
- Alternative: null_resource with local-exec provisioner calling Python script

**Tracking Resource Availability:**
- [Terraform Google Provider Changelog](https://github.com/hashicorp/terraform-provider-google/blob/main/CHANGELOG.md)
- [Terraform Google Provider Issues](https://github.com/hashicorp/terraform-provider-google/issues)
- [Google Cloud Terraform Roadmap](https://github.com/hashicorp/terraform-provider-google/projects)

**Custom Resource Options (if native resource not available):**
1. **null_resource + local-exec** - Call Python deployment script (current approach)
2. **Terraform CDK** - Write custom constructs in Python/TypeScript
3. **Custom Provider** - Build provider for Agent Engine API (high effort)
4. **REST API Data Source** - Use http provider for CRUD operations (limited)

---

## Conclusion

### Recommended Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                        Git Repository                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  terraform/                                                     │
│  ├── setup/              ← One-time CI/CD infrastructure       │
│  │   ├── main.tf         │  (Manual operations)                │
│  │   ├── backend.tf      │  - Service accounts                 │
│  │   ├── outputs.tf      │  - Workload Identity Federation     │
│  │   └── ...             │  - GitHub secrets/variables         │
│  │                       │  - API enablement                   │
│  └── deployment/         ← Per-deployment Agent Engine         │
│      ├── main.tf         │  (CI/CD automated)                  │
│      ├── backend.tf      │  - Agent Engine instances           │
│      ├── data.tf         │  - Deployment config                │
│      └── ...             │  - Uses setup outputs               │
│                                                                 │
│  .github/workflows/                                             │
│  └── deploy-to-agent-engine.yaml  ← Runs deployment Terraform  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ State stored in GCS
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           Google Cloud Storage State Backend                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  gs://project-terraform-state/                                  │
│  ├── setup/                                                     │
│  │   └── default.tfstate  ← Setup module state (stable)        │
│  └── deployment/                                                │
│      └── default.tfstate  ← Deployment state (changes often)   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Next Steps

1. **Immediate (Week 1):**
   - Create GCS state bucket
   - Migrate current Terraform to remote state
   - Test manual operations with remote state

2. **Short-term (Week 2-3):**
   - Split into setup and deployment modules
   - Implement terraform_remote_state data sharing
   - Update GitHub Actions workflow

3. **Long-term (Ongoing):**
   - Monitor for native Agent Engine Terraform resource
   - Consider multi-environment deployment (dev/staging/prod)
   - Explore Terraform testing frameworks (terraform test)

### Critical Success Factors

1. **State Management:** Proper GCS backend configuration with versioning
2. **Clear Boundaries:** Strict separation between setup and deployment modules
3. **Documentation:** Comprehensive README files for both modules
4. **Testing:** Validate state sharing and CI/CD integration before production use
5. **Team Training:** Ensure all developers understand the two-module architecture

### Risk Mitigation

- **Backup state files** before any major changes (GCS versioning handles this)
- **Test in development environment** before applying to production
- **Use terraform plan** extensively to preview changes
- **Maintain rollback procedures** documented in module READMEs
- **Monitor Terraform provider updates** for Agent Engine native resource

---

**Document Version:** 1.0
**Last Updated:** 2025-10-09
**Next Review:** When native Terraform resource for Agent Engine becomes available
