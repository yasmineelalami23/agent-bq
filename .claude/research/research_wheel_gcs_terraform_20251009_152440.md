# Research: Python Wheel Package Uploads to GCS with Terraform-Managed Deployments

**Research Date**: 2025-10-09
**Context**: Agent Engine CI/CD workflow using GitHub Actions + Terraform
**Goal**: Identify production-ready patterns for integrating wheel builds and GCS uploads with Terraform-managed Agent Engine deployments

---

## Executive Summary

**Recommended Approach: External Build → Upload → Terraform Reference Pattern**

The optimal strategy for this project is to **keep wheel building and uploading in GitHub Actions** while using **Terraform data sources to reference the uploaded artifacts**. This separation of concerns aligns with infrastructure-as-code best practices and avoids anti-patterns around using Terraform for build processes.

### Key Recommendations

1. **GitHub Actions handles artifact lifecycle**: Build wheel, upload to GCS, pass metadata to deployment
2. **Terraform manages infrastructure only**: Do NOT use Terraform to upload wheels
3. **Current Python deployment script remains unchanged**: The `deploy_agent.py` script already handles wheel uploads correctly
4. **Use content-based versioning**: Generate unique wheel names using version + git SHA or timestamp
5. **Avoid `null_resource` provisioners**: These are Terraform anti-patterns for build processes

### Critical Insight for This Project

**The current implementation is already optimal.** The `deploy_agent.py` script (lines 249-251, 268, 284) handles wheel package uploads as part of the Agent Engine deployment using Vertex AI's `requirements` and `extra_packages` configuration. The Vertex AI SDK automatically uploads wheels to the staging bucket during `client.agent_engines.create()` or `client.agent_engines.update()` calls.

**No Terraform changes needed for wheel management.**

---

## Detailed Analysis

### 1. Terraform + External Artifacts: Core Patterns

#### Pattern A: External Upload + Data Source Reference (RECOMMENDED)

**How it works:**
- GitHub Actions builds and uploads wheel to GCS
- Terraform uses `data.google_storage_bucket_object` to reference the uploaded file
- Terraform resources consume the data source attributes (md5hash, media_link, etc.)

**Pros:**
- Clean separation of build and infrastructure concerns
- Terraform state only tracks infrastructure, not build artifacts
- Supports external build tools and CI/CD systems
- No Terraform state churn from artifact changes
- Aligns with HashiCorp's "provisioners are a last resort" philosophy

**Cons:**
- Requires coordination between build system and Terraform
- Terraform cannot manage artifact lifecycle (deletion, versioning)
- Need to ensure artifact exists before Terraform runs

**Example:**
```hcl
# Data source to reference externally-uploaded wheel
data "google_storage_bucket_object" "agent_wheel" {
  bucket = var.staging_bucket
  name   = "wheels/${var.agent_name}-${var.version}.whl"
}

# Use in other resources
resource "google_vertex_ai_agent_engine" "agent" {
  # Reference the uploaded wheel
  wheel_uri   = data.google_storage_bucket_object.agent_wheel.media_link
  wheel_hash  = data.google_storage_bucket_object.agent_wheel.md5hash
  # ... other configuration
}
```

#### Pattern B: Terraform-Managed Upload (NOT RECOMMENDED FOR THIS PROJECT)

**How it works:**
- Terraform uses `google_storage_bucket_object` resource to upload wheel
- Terraform tracks the object in state
- Change detection via `source_md5hash` or `detect_md5hash`

**Pros:**
- Single tool manages entire deployment
- Terraform state fully represents deployed infrastructure
- Idempotent uploads with automatic change detection

**Cons:**
- Violates separation of concerns (build vs infrastructure)
- Requires wheel to exist before `terraform apply`
- Terraform state grows with artifact changes
- Forces sequential workflow (build → terraform apply)
- Build failures require Terraform re-runs

**Example:**
```hcl
# Calculate wheel MD5 hash for change detection
locals {
  wheel_file = "agent_engine_cicd_base-${var.version}-py3-none-any.whl"
  wheel_md5  = filemd5(local.wheel_file)
}

# Upload wheel to GCS (managed by Terraform)
resource "google_storage_bucket_object" "agent_wheel" {
  bucket = var.staging_bucket
  name   = "wheels/${local.wheel_file}"
  source = local.wheel_file

  # Trigger replacement when wheel content changes
  source_md5hash = local.wheel_md5

  # Optional: lifecycle management
  lifecycle {
    create_before_destroy = true
  }
}
```

#### Pattern C: `null_resource` with `local-exec` Provisioner (ANTI-PATTERN)

**How it works:**
- Use `null_resource` with `local-exec` provisioner to run build scripts
- Terraform executes shell commands to build and upload wheel
- Triggers based on file changes or timestamp

**Pros:**
- Single `terraform apply` command runs entire workflow
- Can integrate custom build logic

**Cons:**
- **HashiCorp explicitly discourages this**: "Provisioners are a last resort"
- Non-idempotent (builds may not be reproducible)
- State management complexity with triggers
- Error handling is difficult
- Testing and debugging challenges
- Platform-dependent (shell scripts vary by OS)
- Breaks Terraform's declarative model

**HashiCorp's Guidance:**
> "Provisioners should only be used as a last resort. For most common situations there are better alternatives."

**Why this is an anti-pattern:**
- Build processes belong in CI/CD systems, not infrastructure tools
- Terraform is designed for infrastructure state management, not build orchestration
- Creates tight coupling between build and infrastructure

---

### 2. GCS Object Management: `google_storage_bucket_object` Resource

#### Resource Capabilities

From Terraform documentation, the `google_storage_bucket_object` resource provides:

**Upload Methods:**
- `source`: Upload from local file path
- `content`: Upload string content directly

**Change Detection:**
- `detect_md5hash`: Automatically detects changes to local file or server-side modifications
- `source_md5hash`: User-provided Base64 MD5 hash to trigger replacement
  - Recommended usage: `source_md5hash = filemd5("file.whl")`
  - Forces object replacement when wheel content changes

**Versioning and Metadata:**
- `generation`: Object version number (computed, used for versioning and soft delete)
- `md5hash`: Base64 MD5 hash of uploaded data (computed)
- `crc32c`: Base64 CRC32C hash (computed)
- `metadata`: User-provided key/value pairs

**Output Attributes:**
- `self_link`: GCS object URL (gs://bucket/object format)
- `media_link`: Direct download URL (https://storage.googleapis.com/...)
- `output_name`: Safe name for interpolations

#### Change Detection Strategy

**Option 1: `source_md5hash` (Recommended for Terraform-managed uploads)**
```hcl
resource "google_storage_bucket_object" "wheel" {
  bucket = "staging-bucket"
  name   = "wheels/agent-${var.version}.whl"
  source = local.wheel_file

  # Terraform replaces object when file content changes
  source_md5hash = filemd5(local.wheel_file)
}
```

**Option 2: `detect_md5hash` (Automatic detection)**
```hcl
resource "google_storage_bucket_object" "wheel" {
  bucket = "staging-bucket"
  name   = "wheels/agent-${var.version}.whl"
  source = local.wheel_file

  # Automatically detects local file changes
  detect_md5hash = true
}
```

**Warning from Terraform docs:**
> "For dynamically populated files or objects, `detect_md5hash` cannot track or detect changes and will not trigger updates to the objects in the bucket. Please use `source_md5hash` instead."

#### Data Source: `google_storage_bucket_object`

Used to reference externally-managed objects:

```hcl
data "google_storage_bucket_object" "wheel" {
  bucket = "staging-bucket"
  name   = "wheels/agent-0.3.0-abc123.whl"
}

# Available attributes
output "wheel_info" {
  value = {
    md5hash      = data.google_storage_bucket_object.wheel.md5hash
    crc32c       = data.google_storage_bucket_object.wheel.crc32c
    media_link   = data.google_storage_bucket_object.wheel.media_link
    generation   = data.google_storage_bucket_object.wheel.generation
    content_type = data.google_storage_bucket_object.wheel.content_type
  }
}
```

---

### 3. Build-Upload-Deploy Flow: GitHub Actions + Terraform Integration

#### Current Project Architecture Analysis

The existing project already implements the optimal pattern:

**Current GitHub Actions Workflow** (`.github/workflows/deploy-to-agent-engine.yaml`):
```yaml
steps:
  - Install uv
  - Install dependencies (uv sync)
  - Build wheel (uv build --wheel --out-dir .)
  - Deploy agent (uv run deploy)  # ← This uploads the wheel
```

**Current Deployment Script** (`src/deployment/deploy_agent.py`):
```python
# Lines 249-251: Wheel file discovery
wheel_file = get_wheel_file()
requirements = [wheel_file.name]
extra_packages = [wheel_file.name]

# Lines 263-274 or 279-290: Agent Engine deployment
remote_agent = client.agent_engines.create(
    agent=adk_app,
    config={
        "staging_bucket": f"gs://{STAGING_BUCKET}",
        "requirements": requirements,      # ← Vertex AI uploads this
        "extra_packages": extra_packages,  # ← Vertex AI uploads this
        # ... other config
    },
)
```

**Key Insight**: The Vertex AI SDK (`vertexai.Client.agent_engines.create/update`) **automatically handles wheel upload to GCS** when provided via `requirements` and `extra_packages`. The staging bucket path is constructed internally.

**Wheel lifecycle:**
1. GitHub Actions builds wheel locally
2. Deployment script discovers wheel file
3. Vertex AI SDK uploads wheel to `gs://{STAGING_BUCKET}/{GCS_DIR_NAME}/`
4. Agent Engine references the uploaded wheel
5. Local wheel file is deleted (line 316)

#### Alternative Pattern: Explicit GCS Upload (Not needed for this project)

If you wanted to upload wheels independently from Agent Engine deployment:

**GitHub Actions Workflow:**
```yaml
jobs:
  build-and-upload:
    steps:
      - name: Build wheel
        run: uv build --wheel --out-dir dist/

      - name: Generate wheel metadata
        id: wheel-meta
        run: |
          WHEEL_FILE=$(ls dist/*.whl | head -1)
          WHEEL_NAME=$(basename $WHEEL_FILE)
          WHEEL_MD5=$(md5sum $WHEEL_FILE | base64)
          echo "wheel_name=$WHEEL_NAME" >> $GITHUB_OUTPUT
          echo "wheel_md5=$WHEEL_MD5" >> $GITHUB_OUTPUT

      - name: Upload to GCS
        uses: google-github-actions/upload-cloud-storage@v2
        with:
          path: dist/*.whl
          destination: ${{ vars.STAGING_BUCKET }}/wheels/
          parent: false

      - name: Set Terraform variables
        run: |
          echo "WHEEL_NAME=${{ steps.wheel-meta.outputs.wheel_name }}" >> $GITHUB_ENV
          echo "WHEEL_MD5=${{ steps.wheel-meta.outputs.wheel_md5 }}" >> $GITHUB_ENV

      - name: Terraform apply
        run: terraform apply -auto-approve
        env:
          TF_VAR_wheel_name: ${{ env.WHEEL_NAME }}
          TF_VAR_wheel_md5: ${{ env.WHEEL_MD5 }}
```

**Terraform Configuration:**
```hcl
variable "wheel_name" {
  type        = string
  description = "Wheel filename uploaded by GitHub Actions"
}

variable "wheel_md5" {
  type        = string
  description = "MD5 hash of uploaded wheel"
}

# Reference the uploaded wheel
data "google_storage_bucket_object" "agent_wheel" {
  bucket = var.staging_bucket
  name   = "wheels/${var.wheel_name}"
}

# Validate MD5 matches (optional integrity check)
locals {
  md5_matches = data.google_storage_bucket_object.agent_wheel.md5hash == var.wheel_md5
}

check "wheel_integrity" {
  assert {
    condition     = local.md5_matches
    error_message = "Wheel MD5 mismatch - upload may be corrupted"
  }
}
```

---

### 4. Wheel Versioning Strategies

#### Python Wheel Naming Convention

From PEP 427 (Wheel specification):

**Format:**
```
{distribution}-{version}(-{build})?-{python}-{abi}-{platform}.whl
```

**Example:**
```
agent_engine_cicd_base-0.3.0-py3-none-any.whl
```

**Components:**
- `distribution`: Package name (normalized: lowercase, underscores)
- `version`: PEP 440 version (e.g., 0.3.0, 1.0.0a1, 2.1.0rc1)
- `build`: Optional build tag (discouraged for public packages)
- `python`: Language version (py3, py312, py313)
- `abi`: Application Binary Interface (none for pure Python)
- `platform`: Target platform (any, linux_x86_64, etc.)

#### Versioning Strategy Options

**Strategy 1: Semantic Versioning Only (Current Project)**

**How it works:**
- Version defined in `pyproject.toml`
- Wheel name: `agent_engine_cicd_base-0.3.0-py3-none-any.whl`
- Same version = same filename

**Pros:**
- Simple and predictable
- Standard Python packaging practice
- Clear version progression

**Cons:**
- Same filename for rebuilds without version bump
- GCS object overwrites require `generation` tracking
- No automatic differentiation between builds of same version

**Current implementation:**
```toml
# pyproject.toml
[project]
name = "agent-engine-cicd-base"
version = "0.3.0"
```

**Strategy 2: Semantic Version + Build Tag (Recommended for CI/CD)**

**How it works:**
- Append git SHA, build number, or timestamp to version
- Wheel name: `agent_engine_cicd_base-0.3.0+abc123-py3-none-any.whl`

**Pros:**
- Unique filename per build
- Easy to trace builds to commits
- No GCS object overwrites
- Simple rollback (previous build still exists)

**Cons:**
- Requires dynamic version generation
- More complex cleanup (multiple builds accumulate)

**Implementation:**
```yaml
# GitHub Actions
- name: Generate build version
  id: version
  run: |
    BASE_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
    GIT_SHA=$(git rev-parse --short HEAD)
    BUILD_VERSION="${BASE_VERSION}+${GIT_SHA}"
    echo "version=$BUILD_VERSION" >> $GITHUB_OUTPUT

- name: Build wheel with build version
  run: |
    # Update pyproject.toml version
    sed -i "s/^version = .*/version = \"${{ steps.version.outputs.version }}\"/" pyproject.toml
    uv build --wheel --out-dir .
```

**Strategy 3: Semantic Version + Timestamp**

**How it works:**
- Append ISO 8601 timestamp to version
- Wheel name: `agent_engine_cicd_base-0.3.0+20251009152440-py3-none-any.whl`

**Pros:**
- Chronological ordering
- Unique per build
- Easy to identify when built

**Cons:**
- Harder to correlate with git commits
- Timestamp-based cleanup policies needed

**Strategy 4: GCS Object Versioning (Native GCS Feature)**

**How it works:**
- Enable versioning on GCS bucket
- Same filename, different `generation` numbers
- Each upload creates new version

**Pros:**
- No filename changes needed
- GCS handles version tracking
- Easy rollback via generation numbers
- Automatic lifecycle management

**Cons:**
- Requires additional GCS API calls to manage versions
- More complex to reference specific versions in Terraform
- Storage costs for multiple versions

**GCS Versioning Setup:**
```bash
# Enable versioning
gcloud storage buckets update gs://BUCKET_NAME --versioning

# List object versions
gsutil ls -a gs://BUCKET_NAME/wheels/agent.whl
```

**Terraform reference:**
```hcl
data "google_storage_bucket_object" "wheel" {
  bucket = "staging-bucket"
  name   = "wheels/agent.whl"
  # Uses latest version by default
}

# Reference specific generation
data "google_storage_bucket_object" "wheel_v1" {
  bucket = "staging-bucket"
  name   = "wheels/agent.whl#${var.generation_number}"
}
```

#### Recommended Versioning for This Project

**Current State**: Version 0.3.0 in `pyproject.toml`, static versioning

**Recommendation**: **Implement Strategy 2 (Semantic Version + Git SHA)**

**Rationale:**
1. Provides unique identifiers for each build
2. Traceable to source code commits
3. Supports rollback without GCS versioning complexity
4. No additional GCS API costs
5. Simple to implement in GitHub Actions

**Implementation Proposal:**

```yaml
# .github/workflows/deploy-to-agent-engine.yaml
jobs:
  deploy:
    steps:
      - name: Checkout code
        uses: actions/checkout@v5
        with:
          fetch-depth: 0  # Fetch all history for git describe

      - name: Generate build version
        id: build-version
        run: |
          BASE_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
          GIT_SHA=$(git rev-parse --short HEAD)
          BUILD_VERSION="${BASE_VERSION}+git${GIT_SHA}"
          echo "version=$BUILD_VERSION" >> $GITHUB_OUTPUT
          echo "Building version: $BUILD_VERSION"

      - name: Update version in pyproject.toml
        run: |
          sed -i "s/^version = .*/version = \"${{ steps.build-version.outputs.version }}\"/" pyproject.toml

      - name: Build wheel
        run: uv build --wheel --out-dir .

      # Rest of workflow remains unchanged
      - name: Deploy agent
        run: uv run deploy
```

**Resulting wheel name:**
```
agent_engine_cicd_base-0.3.0+gitabc123-py3-none-any.whl
```

---

### 5. Change Detection and Agent Engine Updates

#### How Vertex AI Detects Changes

The Vertex AI Agent Engine SDK does NOT have built-in wheel change detection. The update behavior depends on the `AGENT_ENGINE_ID` environment variable:

**Current Implementation** (`deploy_agent.py`):
```python
if AGENT_ENGINE_ID:
    # Update existing agent engine
    remote_agent = client.agent_engines.update(
        name=f"projects/{PROJECT}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}",
        agent=adk_app,
        config={...}
    )
else:
    # Create new agent engine
    remote_agent = client.agent_engines.create(
        agent=adk_app,
        config={...}
    )
```

**Key Behavior:**
- `AGENT_ENGINE_ID` set = **update** existing instance
- `AGENT_ENGINE_ID` not set = **create** new instance
- No automatic wheel hash comparison

**Problem**: If wheel content changes but `AGENT_ENGINE_ID` remains the same, the update uploads the new wheel but may not force a full redeployment if the Agent Engine runtime hasn't been updated.

#### Solution: Force Updates with Unique Identifiers

**Option 1: Version-based Updates (Current Project Approach)**

Track the version and force updates:

```python
# deploy_agent.py - add version tracking
CURRENT_VERSION = "0.3.0+gitabc123"  # From environment or pyproject.toml

# Add version to environment variables
AGENT_ENV_VARS = {
    "AGENT_NAME": AGENT_NAME,
    "AGENT_VERSION": CURRENT_VERSION,  # ← New
    "LOG_LEVEL": safe_getenv("LOG_LEVEL", "INFO"),
}
```

**Option 2: Wheel Hash Validation**

Compare wheel MD5 before/after upload:

```python
import hashlib
from pathlib import Path

def calculate_wheel_md5(wheel_path: Path) -> str:
    """Calculate Base64 MD5 hash of wheel file."""
    import base64
    md5_hash = hashlib.md5(wheel_path.read_bytes()).digest()
    return base64.b64encode(md5_hash).decode()

# In deploy()
wheel_file = get_wheel_file()
wheel_md5 = calculate_wheel_md5(wheel_file)

print(f"📦 Wheel MD5: {wheel_md5}")

# Add to Agent Engine config for tracking
AGENT_ENV_VARS["WHEEL_MD5"] = wheel_md5
```

**Option 3: Force Recreate on Major Changes**

For breaking changes, create new instance instead of updating:

```python
# deploy_agent.py
FORCE_RECREATE = os.getenv("FORCE_RECREATE", "false").lower() == "true"

if AGENT_ENGINE_ID and not FORCE_RECREATE:
    # Update existing
    remote_agent = client.agent_engines.update(...)
else:
    # Create new (even if AGENT_ENGINE_ID exists)
    remote_agent = client.agent_engines.create(...)
```

---

### 6. GitHub Actions Workflow Recommendations

#### Optimal Workflow Structure

```yaml
name: Deploy to Agent Engine

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      force_recreate:
        description: 'Force recreate Agent Engine (instead of update)'
        required: false
        type: boolean
        default: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v5
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version-file: pyproject.toml

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}
          create_credentials_file: true

      # Build version generation (RECOMMENDED ADDITION)
      - name: Generate build version
        id: version
        run: |
          BASE_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
          GIT_SHA=$(git rev-parse --short HEAD)
          BUILD_VERSION="${BASE_VERSION}+git${GIT_SHA}"
          echo "version=$BUILD_VERSION" >> $GITHUB_OUTPUT
          echo "::notice::Building version $BUILD_VERSION"

      - name: Update pyproject.toml version
        run: |
          sed -i "s/^version = .*/version = \"${{ steps.version.outputs.version }}\"/" pyproject.toml

      - name: Install uv
        uses: astral-sh/setup-uv@v6

      - name: Install dependencies
        run: uv sync --frozen

      - name: Build wheel
        run: uv build --wheel --out-dir .

      # Current deployment process (UNCHANGED)
      - name: Deploy agent
        run: uv run deploy
        env:
          PYTHONUNBUFFERED: "1"
          FORCE_RECREATE: ${{ inputs.force_recreate || 'false' }}
          # ... existing environment variables

      # Optional: Upload wheel artifact for debugging
      - name: Upload wheel artifact
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: wheel-${{ steps.version.outputs.version }}
          path: "*.whl"
          retention-days: 30
```

#### Environment Variable Management

**Current Terraform Configuration** (`terraform/github.tf`):

The project already synchronizes `.env` variables to GitHub Actions variables:

```hcl
locals {
  all_workflow_keys = toset([
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_CLOUD_STORAGE_BUCKET",
    "GCS_DIR_NAME",
    "AGENT_NAME",
    "AGENT_DISPLAY_NAME",
    "AGENT_DESCRIPTION",
    "AGENT_ENGINE_ID",
    "LOG_LEVEL",
    "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT",
    "AGENTSPACE_APP_ID",
    "AGENTSPACE_APP_LOCATION",
  ])

  github_variables = {
    for key in keys(data.dotenv.adk.entries) :
    key => data.dotenv.adk.entries[key]
    if contains(local.all_workflow_keys, key) && data.dotenv.adk.entries[key] != ""
  }
}

resource "github_actions_variable" "variable" {
  for_each      = local.github_variables
  repository    = local.repository_name
  variable_name = each.key
  value         = each.value
}
```

**No changes needed** - this configuration already supports the deployment workflow.

---

### 7. Pros/Cons Comparison: Terraform-Managed vs External Upload

#### External Upload (GitHub Actions) - RECOMMENDED

**Pros:**
- ✅ Separation of concerns (build in CI, infrastructure in Terraform)
- ✅ Terraform state remains infrastructure-focused
- ✅ Supports complex build pipelines
- ✅ Flexible versioning strategies
- ✅ Parallel workflows (build ≠ infrastructure changes)
- ✅ Standard CI/CD practice
- ✅ Works with current implementation (no changes needed)

**Cons:**
- ❌ Coordination required between GitHub Actions and deployment
- ❌ Wheel must exist before deployment runs
- ❌ Terraform doesn't track artifact lifecycle

**Best for:**
- Production deployments
- Multi-stage CI/CD pipelines
- Projects with complex build requirements
- Teams separating build and infrastructure responsibilities

#### Terraform-Managed Upload

**Pros:**
- ✅ Single command deployment (`terraform apply`)
- ✅ Terraform state tracks all resources
- ✅ Idempotent uploads with hash-based change detection
- ✅ Native lifecycle management

**Cons:**
- ❌ Violates infrastructure-as-code separation of concerns
- ❌ Build must complete before Terraform runs
- ❌ Terraform state churn from artifact changes
- ❌ Harder to implement complex build pipelines
- ❌ Forces sequential workflow
- ❌ Not compatible with current Vertex AI SDK upload pattern

**Best for:**
- Simple proof-of-concept deployments
- Single-file artifacts with minimal build steps
- Projects where all changes are infrastructure-related

#### null_resource Provisioners - ANTI-PATTERN

**Pros:**
- ✅ Single command runs entire workflow

**Cons:**
- ❌ **Explicitly discouraged by HashiCorp**
- ❌ Non-idempotent
- ❌ Platform-dependent
- ❌ Poor error handling
- ❌ Breaks declarative infrastructure model
- ❌ Difficult to test and debug
- ❌ State management complexity

**Best for:**
- **Nothing** - avoid this pattern

---

## Implementation Recommendations

### For This Specific Project

**Current State Assessment:**
- ✅ GitHub Actions builds wheel
- ✅ Python deployment script uploads wheel via Vertex AI SDK
- ✅ Terraform manages GCP infrastructure and GitHub secrets/variables
- ✅ Clean separation of concerns already implemented

**Recommended Changes:**

#### 1. Add Build Versioning (Optional but Recommended)

**Goal**: Generate unique wheel filenames per build

**Changes:**
```yaml
# .github/workflows/deploy-to-agent-engine.yaml
- name: Generate build version
  id: version
  run: |
    BASE_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
    GIT_SHA=$(git rev-parse --short HEAD)
    BUILD_VERSION="${BASE_VERSION}+git${GIT_SHA}"
    echo "version=$BUILD_VERSION" >> $GITHUB_OUTPUT

- name: Update pyproject.toml version
  run: |
    sed -i "s/^version = .*/version = \"${{ steps.version.outputs.version }}\"/" pyproject.toml
```

**Benefit**: Unique, traceable wheel filenames for each deployment

#### 2. Add Wheel Artifact Upload (Optional)

**Goal**: Preserve wheel artifacts for debugging and rollback

**Changes:**
```yaml
- name: Upload wheel artifact
  uses: actions/upload-artifact@v4
  if: always()
  with:
    name: wheel-${{ steps.version.outputs.version }}
    path: "*.whl"
    retention-days: 30
```

**Benefit**: Download and inspect wheels from GitHub Actions UI

#### 3. Document GCS Staging Bucket Structure

**Goal**: Clarify where wheels are stored

**Current Implementation:**
- Vertex AI SDK uploads to: `gs://{STAGING_BUCKET}/{GCS_DIR_NAME}/`
- Default `GCS_DIR_NAME`: `agent-engine-staging`

**Documentation Addition:**
```markdown
## Wheel Storage Location

Wheels are uploaded to GCS during Agent Engine deployment:

- **Bucket**: `gs://{GOOGLE_CLOUD_STORAGE_BUCKET}/`
- **Directory**: `{GCS_DIR_NAME}/` (default: `agent-engine-staging/`)
- **Managed by**: Vertex AI SDK (automatic during `client.agent_engines.create/update`)

To list deployed wheels:
```bash
gsutil ls gs://{GOOGLE_CLOUD_STORAGE_BUCKET}/{GCS_DIR_NAME}/
```
```

#### 4. NO Terraform Changes Needed

**Current Terraform configuration is optimal:**
- Manages GCP infrastructure (IAM, APIs, WIF)
- Synchronizes environment variables to GitHub Actions
- Does NOT manage wheels (correct separation of concerns)

**Do NOT add:**
- ❌ `google_storage_bucket_object` resources for wheels
- ❌ `null_resource` provisioners for builds
- ❌ Data sources for wheel objects (not needed for current flow)

---

## Code Examples

### Example 1: Enhanced GitHub Actions Workflow

```yaml
name: Deploy to Agent Engine

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout
        uses: actions/checkout@v5
        with:
          fetch-depth: 0

      - name: Generate build version
        id: version
        run: |
          BASE=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
          SHA=$(git rev-parse --short HEAD)
          VERSION="${BASE}+git${SHA}"
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "::notice::Building version $VERSION"

      - name: Update version
        run: |
          sed -i "s/^version = .*/version = \"${{ steps.version.outputs.version }}\"/" pyproject.toml

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - name: Install uv
        uses: astral-sh/setup-uv@v6

      - name: Install dependencies
        run: uv sync --frozen

      - name: Build wheel
        run: uv build --wheel --out-dir .

      - name: Deploy agent
        run: uv run deploy
        env:
          PYTHONUNBUFFERED: "1"
          # Variables from Terraform
          GOOGLE_GENAI_USE_VERTEXAI: ${{ vars.GOOGLE_GENAI_USE_VERTEXAI }}
          GOOGLE_CLOUD_PROJECT: ${{ vars.GOOGLE_CLOUD_PROJECT }}
          GOOGLE_CLOUD_LOCATION: ${{ vars.GOOGLE_CLOUD_LOCATION }}
          GOOGLE_CLOUD_STORAGE_BUCKET: ${{ vars.GOOGLE_CLOUD_STORAGE_BUCKET }}
          GCS_DIR_NAME: ${{ vars.GCS_DIR_NAME }}
          AGENT_NAME: ${{ vars.AGENT_NAME }}
          AGENT_ENGINE_ID: ${{ vars.AGENT_ENGINE_ID }}

      - name: Upload wheel artifact
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: wheel-${{ steps.version.outputs.version }}
          path: "*.whl"
          retention-days: 30
```

### Example 2: Enhanced Deployment Script with Version Tracking

```python
# src/deployment/deploy_agent.py
import hashlib
import base64
from pathlib import Path

def calculate_wheel_metadata(wheel_path: Path) -> dict:
    """Calculate metadata for wheel package.

    Args:
        wheel_path: Path to wheel file

    Returns:
        Dictionary with name, md5, and size
    """
    wheel_content = wheel_path.read_bytes()
    md5_hash = base64.b64encode(hashlib.md5(wheel_content).digest()).decode()

    return {
        "name": wheel_path.name,
        "md5": md5_hash,
        "size": len(wheel_content),
    }

def deploy() -> None:
    """Deploy with enhanced wheel tracking."""
    from agent.agent import root_agent
    from agent.utils.observability import setup_opentelemetry

    # Get wheel and calculate metadata
    wheel_file = get_wheel_file()
    wheel_meta = calculate_wheel_metadata(wheel_file)

    print(f"📦 Wheel: {wheel_meta['name']}")
    print(f"🔐 MD5: {wheel_meta['md5']}")
    print(f"📏 Size: {wheel_meta['size']:,} bytes")

    # Add metadata to environment variables for runtime tracking
    AGENT_ENV_VARS["WHEEL_VERSION"] = wheel_meta["name"]
    AGENT_ENV_VARS["WHEEL_MD5"] = wheel_meta["md5"]

    # Rest of deployment unchanged
    requirements = [wheel_file.name]
    extra_packages = [wheel_file.name]

    adk_app = AdkApp(
        agent=root_agent,
        enable_tracing=ENABLE_TRACING,
        instrumentor_builder=setup_opentelemetry,
    )

    # Deploy...
```

### Example 3: GCS Lifecycle Management (Optional)

If you want to automatically clean up old wheels:

```hcl
# terraform/storage.tf
resource "google_storage_bucket" "staging" {
  name     = var.staging_bucket
  location = var.location

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  # Auto-delete old wheels after 30 days
  lifecycle_rule {
    condition {
      age = 30
      matches_prefix = ["${var.gcs_dir_name}/"]
    }
    action {
      type = "Delete"
    }
  }

  # Keep recent wheels (last 10 versions)
  lifecycle_rule {
    condition {
      num_newer_versions = 10
      matches_prefix     = ["${var.gcs_dir_name}/"]
    }
    action {
      type = "Delete"
    }
  }
}
```

---

## Conclusion

**For this project, the current implementation is already optimal.** The separation of concerns is correct:

1. **GitHub Actions**: Builds wheels
2. **Python deployment script**: Uploads wheels via Vertex AI SDK
3. **Terraform**: Manages infrastructure and GitHub configuration

**Recommended enhancements:**
- Add build versioning (git SHA) to wheel filenames
- Upload wheel artifacts to GitHub Actions for debugging
- Document GCS staging bucket structure

**Do NOT implement:**
- Terraform-managed wheel uploads
- `null_resource` provisioners for builds
- Complex Terraform change detection for wheels

This approach aligns with infrastructure-as-code best practices, maintains clean separation of concerns, and supports production-grade CI/CD workflows.

---

## References

### Terraform Documentation
- [google_storage_bucket_object resource](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_object)
- [google_storage_bucket_object data source](https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/storage_bucket_object)
- [Provisioners are a Last Resort](https://developer.hashicorp.com/terraform/language/resources/provisioners/syntax#provisioners-are-a-last-resort)
- [Managing Infrastructure as Code](https://cloud.google.com/architecture/managing-infrastructure-as-code)

### Google Cloud Storage
- [Hashes and ETags: Best Practices](https://cloud.google.com/storage/docs/hashes-etags)
- [Object Versioning](https://cloud.google.com/storage/docs/object-versioning)
- [Lifecycle Management](https://cloud.google.com/storage/docs/lifecycle)

### Python Packaging
- [PEP 427: The Wheel Binary Package Format](https://peps.python.org/pep-0427/)
- [Python Packaging Specifications](https://packaging.python.org/en/latest/specifications/)

### Project Files
- `.github/workflows/deploy-to-agent-engine.yaml` - Current GitHub Actions workflow
- `src/deployment/deploy_agent.py` - Deployment script with Vertex AI SDK integration
- `terraform/github.tf` - GitHub Actions variable synchronization
- `pyproject.toml` - Project metadata and versioning

### Key Insights
1. Vertex AI SDK handles wheel uploads automatically when using `extra_packages`
2. Terraform should manage infrastructure, not build artifacts
3. Content-based versioning (git SHA) provides unique, traceable artifacts
4. Separation of concerns is critical for maintainable CI/CD pipelines
