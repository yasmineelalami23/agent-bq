# UX Design Brief: Terraform Migration for Agent Engine Deployment

**Project:** agent-engine-cicd-base Template Repository Migration
**Date:** 2025-10-09
**Design Focus:** Developer Experience for Infrastructure-as-Code Migration

---

## Executive Summary

This design brief addresses the developer experience for migrating from Python-based to Terraform-managed Agent Engine deployments. The migration introduces the native `google_vertex_ai_reasoning_engine` Terraform resource while maintaining two critical usage paths: quick prototyping (clone → test locally) and production development (template → CI/CD → deploy). The design prioritizes maintaining the streamlined 4-step quickstart workflow while introducing infrastructure-as-code benefits.

**Key Design Principles:**
- Progressive disclosure of Terraform complexity for Python developers
- Clear mental models for "setup once" vs "deploy repeatedly" separation
- Zero-friction path for existing users
- Fail-fast with helpful error messages

---

## 1. User Journey Mapping

### 1.1 Current 4-Step Quickstart Journey

```
┌─────────────┐    ┌──────────┐    ┌──────────────┐    ┌─────────┐
│   Setup     │───▶│  Develop │───▶│   Provision  │───▶│ Deploy  │
│  (1 hour)   │    │ (ongoing)│    │   (5 min)    │    │ (2 min) │
└─────────────┘    └──────────┘    └──────────────┘    └─────────┘
     │                   │                 │                 │
     ▼                   ▼                 ▼                 ▼
- Create repo       - Test locally    - Run terraform    - Push code
- Install UV        - Modify agent    - Apply infra      - PR workflow
- Configure .env    - Iterate         - Get secrets      - Auto-deploy
```

**Pain Points:**
- Phase 2 manual capture of `AGENT_ENGINE_ID` from logs
- Unclear when to use Python vs Terraform commands
- Risk of creating duplicate Agent Engine instances

### 1.2 Updated Journey with Terraform Agent Engine

```
┌─────────────┐    ┌──────────┐    ┌──────────────────────────┐    ┌─────────┐
│   Setup     │───▶│  Develop │───▶│      Provision           │───▶│ Deploy  │
│  (1 hour)   │    │ (ongoing)│    │   Setup + Deployment     │    │ (2 min) │
└─────────────┘    └──────────┘    │      (8-10 min)         │    └─────────┘
     │                   │         └──────────────────────────┘         │
     ▼                   ▼                      │                        ▼
- Create repo       - Test locally         ┌───┴───┐              - Push code
- Install UV        - Modify agent    ┌────┴───┐ ┌─┴────┐        - PR workflow
- Configure .env    - Iterate         │ Setup  │ │Deploy│        - Auto-update
                                      │(5 min) │ │(3min)│
                                      └────────┘ └──────┘
                                          │         │
                                          ▼         ▼
                                    - Run setup   - Run deploy
                                    - Get secrets - Create agent
                                    - Enable APIs - No manual ID!
```

**Key Changes:**
- **Eliminated:** Manual Phase 2 (ID capture and sync)
- **Split:** Terraform into two modules (setup infrastructure vs deploy agent)
- **Automated:** Agent Engine ID management via Terraform state
- **Preserved:** Same overall 4-step workflow structure

### 1.3 User Personas and Their Journeys

#### Persona A: Python Developer New to Terraform

**Journey:**
1. **Setup:** Follows quickstart, confused by "Terraform" mentions
2. **Develop:** Comfortable with `uv run local-agent`
3. **Provision:**
   - Hesitant at `terraform init` command
   - Needs clear explanation of what Terraform does
   - Appreciates wrapper script options
4. **Deploy:** Relief that GitHub Actions handles complexity

**Design Needs:**
- Progressive disclosure (hide Terraform details initially)
- Escape hatches to Python-only workflow for prototyping
- Clear analogies (Terraform = "infrastructure blueprints")

#### Persona B: DevOps Engineer Familiar with Terraform

**Journey:**
1. **Setup:** Immediately understands two-module architecture
2. **Develop:** May skip local testing, focuses on Terraform
3. **Provision:**
   - Appreciates separated concerns
   - May want to customize backend configuration
   - Looks for remote state options
4. **Deploy:** Wants to understand Terraform resource details

**Design Needs:**
- Direct access to Terraform configurations
- Clear documentation of resource dependencies
- Flexibility to customize state management

#### Persona C: Existing User Migrating

**Journey:**
1. **Discovery:** Learns about Terraform migration from changelog
2. **Assessment:** Evaluates impact on existing deployment
3. **Migration:**
   - Needs to import existing Agent Engine
   - Concerned about downtime
   - Wants rollback options
4. **Validation:** Tests that everything still works

**Design Needs:**
- Clear migration guide with rollback procedures
- Import instructions for existing resources
- Compatibility guarantees for Python workflow

---

## 2. Developer Experience States

### 2.1 First-Time Setup State

**Current Experience:**
```
Developer: "I need to deploy an AI agent"
README: "Run these 4 steps..."
[After Step 3]: "Now capture the AGENT_ENGINE_ID from logs"
Developer: "Wait, what? Where are the logs?"
```

**Improved Experience:**
```
Developer: "I need to deploy an AI agent"
README: "Choose your path:"

🚀 Quick Start (Recommended for first-time users)
────────────────────────────────────────────────
Step 1: Setup environment
Step 2: Test locally
Step 3: Provision infrastructure (one command!)
Step 4: Deploy (automatic - no manual steps!)

📦 Already have an agent deployed?
──────────────────────────────────
→ See migration guide
```

**UI Elements:**
- Clear path selection (quick start vs migration)
- Visual progress indicators
- Success confirmations at each step
- No manual ID management

### 2.2 Local Development State

**Experience remains unchanged:**
```bash
# Test your agent locally (same as before)
uv run local-agent

# Output includes:
🤖 Agent running at http://localhost:8000
📝 Logs: Cloud Logging (project: my-project)
🔍 Traces: Cloud Trace (view in console)
```

**Key:** Local development experience is preserved exactly - no Terraform involvement.

### 2.3 CI/CD Setup State

**Current Pain:**
```
Step 1: terraform apply
[Success]
Step 2: Push to trigger deployment
[GitHub Actions runs]
Step 3: Find AGENT_ENGINE_ID in logs
[Manual search through GitHub Actions output]
Step 4: Update .env with ID
Step 5: terraform apply again
[Finally done]
```

**Improved Flow:**
```
Step 1: Provision setup infrastructure
$ cd terraform/setup && terraform apply
✅ Service accounts created
✅ GitHub secrets configured
✅ APIs enabled

Step 2: Provision Agent Engine
$ cd ../deployment && terraform apply
✅ Agent Engine created
✅ ID managed automatically
✅ Ready for deployments

Step 3: Push code to deploy updates
$ git push origin main
[GitHub Actions automatically updates agent]
```

**Visual Feedback:**
```
terraform apply

Terraform will perform the following actions:

  # google_vertex_ai_reasoning_engine.agent will be created
  + resource "google_vertex_ai_reasoning_engine" "agent" {
      + display_name = "my-agent"
      + region       = "us-central1"
      ...
    }

Plan: 1 to add, 0 to change, 0 to destroy.

Do you want to perform these actions?
  Enter a value: yes

google_vertex_ai_reasoning_engine.agent: Creating...
⏳ This may take 2-3 minutes...
google_vertex_ai_reasoning_engine.agent: Creation complete!

Outputs:
agent_engine_id = "1234567890"
agent_url = "https://console.cloud.google.com/vertex-ai/..."

✅ Agent Engine deployed successfully!
```

### 2.4 Ongoing Deployments State

**Experience:**
```bash
# Make code changes
vim src/agent/agent.py

# Commit and push
git add -A
git commit -m "feat: add new tool"
git push origin feature-branch

# Create PR
gh pr create

# After review and merge
[GitHub Actions runs automatically]
[Agent updates in place - no manual intervention]
```

**GitHub Actions Output:**
```
▶ Deploy to Agent Engine

✓ Checkout code
✓ Build wheel package
✓ Setup Terraform
✓ Terraform Plan
  ~ Updating agent engine in-place
✓ Terraform Apply
✓ Capture outputs
  agent_engine_id: 1234567890
✓ Register with Agentspace (if configured)

✅ Deployment complete!
```

### 2.5 Troubleshooting State

**Common Failure: Terraform State Lock**
```
Error: Error acquiring state lock

Another Terraform process is running or the lock is stuck.

💡 Quick Fix:
1. Check if another deployment is running
2. If not, force unlock:
   terraform force-unlock <LOCK_ID>

Need help? See: docs/troubleshooting.md#state-lock
```

**Common Failure: Pickle File Issues**
```
Error: Package spec requires pickle_object_gcs_uri

The Terraform resource needs a pickle file but none was created.

💡 Quick Fix:
1. Ensure build process creates pickle file:
   python scripts/create_pickle.py

2. Or use Python deployment (fallback):
   uv run deploy

Need help? See: docs/troubleshooting.md#pickle-creation
```

**Common Failure: Missing Permissions**
```
Error: googleapi: Error 403: Permission denied

Service account lacks required permissions.

💡 Quick Fix:
1. Check service account roles:
   terraform -chdir=terraform/setup plan

2. Ensure APIs are enabled:
   terraform -chdir=terraform/setup apply

Detected issue: Missing role 'roles/aiplatform.user'
Run: terraform -chdir=terraform/setup apply to fix
```

---

## 3. Command Line Interface

### 3.1 Command Evolution

**Current Commands:**
```bash
# Infrastructure setup
terraform -chdir=terraform init
terraform -chdir=terraform apply

# Agent deployment
uv run deploy        # Creates or updates agent
uv run delete        # Deletes agent
uv run local-agent   # Test locally
uv run remote-agent  # Test deployed
```

**Proposed Commands:**

#### Option A: Terraform-Native (Purist Approach)
```bash
# Setup infrastructure (one-time)
terraform -chdir=terraform/setup init
terraform -chdir=terraform/setup apply

# Deploy agent (Terraform-managed)
terraform -chdir=terraform/deployment init
terraform -chdir=terraform/deployment apply

# Test commands (unchanged)
uv run local-agent
uv run remote-agent
```

#### Option B: Wrapper Scripts (Recommended)
```bash
# Setup infrastructure (one-time)
uv run terraform-setup

# Deploy agent (simplified)
uv run terraform-deploy

# Fallback for Python-only
uv run deploy --legacy

# Test commands (unchanged)
uv run local-agent
uv run remote-agent
```

**Wrapper Implementation:**
```toml
# pyproject.toml
[project.scripts]
terraform-setup = "scripts.terraform_wrapper:setup"
terraform-deploy = "scripts.terraform_wrapper:deploy"
terraform-destroy = "scripts.terraform_wrapper:destroy"
```

```python
# scripts/terraform_wrapper.py
"""Terraform wrapper for Python developers."""

import subprocess
import sys
from pathlib import Path

def setup():
    """Run Terraform setup module."""
    print("🔧 Setting up CI/CD infrastructure...")
    print("This configures service accounts, APIs, and GitHub secrets.\n")

    terraform_dir = Path("terraform/setup")

    # Check if already initialized
    if not (terraform_dir / ".terraform").exists():
        print("Initializing Terraform...")
        subprocess.run(["terraform", "init"], cwd=terraform_dir, check=True)

    print("\nPlanning infrastructure changes...")
    subprocess.run(["terraform", "plan"], cwd=terraform_dir, check=True)

    response = input("\nApply these changes? (yes/no): ")
    if response.lower() == 'yes':
        subprocess.run(["terraform", "apply", "-auto-approve"],
                      cwd=terraform_dir, check=True)
        print("\n✅ Setup complete!")
    else:
        print("❌ Setup cancelled")
        sys.exit(1)

def deploy():
    """Run Terraform deployment module."""
    print("🚀 Deploying Agent Engine...")

    # Build wheel first
    print("Building wheel package...")
    subprocess.run(["uv", "build", "--wheel", "--out-dir", "."], check=True)

    terraform_dir = Path("terraform/deployment")

    if not (terraform_dir / ".terraform").exists():
        print("Initializing Terraform...")
        subprocess.run(["terraform", "init"], cwd=terraform_dir, check=True)

    print("\nDeploying agent...")
    subprocess.run(["terraform", "apply", "-auto-approve"],
                  cwd=terraform_dir, check=True)

    print("\n✅ Agent deployed successfully!")
```

### 3.2 Making Terraform Approachable

**Strategy 1: Hide Complexity Behind Familiar Commands**
```bash
# What Python developers expect
uv run deploy

# What actually happens (hidden)
1. Build wheel
2. Create pickle
3. Upload to GCS
4. Run Terraform apply
5. Clean up artifacts
```

**Strategy 2: Provide Escape Hatches**
```bash
# When Terraform fails, offer Python fallback
Error: Terraform deployment failed

You can still deploy using Python (legacy mode):
  uv run deploy --legacy

This uses the previous deployment method.
Consider filing an issue if Terraform consistently fails.
```

**Strategy 3: Progressive Disclosure**
```bash
# Level 1: Simple command
uv run terraform-deploy

# Level 2: With options
uv run terraform-deploy --plan-only
uv run terraform-deploy --var="log_level=DEBUG"

# Level 3: Direct Terraform (power users)
cd terraform/deployment
terraform plan -var="agent_display_name=Custom Agent"
terraform apply
```

---

## 4. Documentation Structure

### 4.1 README.md Changes

**Current Structure:**
```markdown
## Quickstart (4 steps)
1. Setup
2. Develop/Prototype
3. Provision Infrastructure
4. Trigger Deployment

## Documentation
- Getting Started
- Deployment
- Production Features
- API Reference
```

**Updated Structure:**
```markdown
## 🚀 Quickstart (4 steps)

### Choose Your Path:

#### 🎯 New Project (Recommended)
Follow our streamlined 4-step process with automatic infrastructure management.

#### 🔄 Migrating Existing Agent?
See our [migration guide](docs/migration_from_python.md) for zero-downtime transition.

### Step 1: Setup (5 minutes)
[Unchanged content]

### Step 2: Develop/Prototype (ongoing)
[Unchanged content]

### Step 3: Provision Infrastructure (8-10 minutes)

We now use Terraform to manage infrastructure as code, providing better reliability and state management.

#### 3a. Setup Infrastructure (one-time, 5 minutes)
```bash
# Option 1: Using our wrapper (recommended)
uv run terraform-setup

# Option 2: Direct Terraform
cd terraform/setup
terraform init
terraform apply
```

This creates:
- ✅ Service accounts and IAM roles
- ✅ GitHub secrets and variables
- ✅ Workload Identity Federation
- ✅ Required Google Cloud APIs

#### 3b. Deploy Agent Engine (3 minutes)
```bash
# Option 1: Using our wrapper (recommended)
uv run terraform-deploy

# Option 2: Direct Terraform
cd terraform/deployment
terraform init
terraform apply
```

This creates:
- ✅ Agent Engine instance (automatic ID management!)
- ✅ GCS staging bucket
- ✅ Runtime configuration

**🎉 No more manual ID capture!** Terraform manages the Agent Engine ID automatically.

### Step 4: Trigger Deployment [Unchanged]

## 📚 Documentation

### Getting Started
- [README](README.md) - You are here
- [Development Guide](docs/development.md) - Local testing and commands
- **[Migration Guide](docs/migration_from_python.md)** - For existing users

### Infrastructure Management (New!)
- **[Terraform Architecture](docs/terraform_architecture.md)** - Understanding the two-module design
- **[Setup vs Deployment](docs/setup_vs_deployment.md)** - What goes where and why

### Deployment
- [CI/CD Setup](docs/cicd_setup_github_actions.md) - Now with Terraform!
- [Manual Deployment](docs/development.md#manual-deployment) - Python fallback option
```

### 4.2 New Documentation Files

**`docs/migration_from_python.md`:**
```markdown
# Migrating from Python to Terraform Deployment

## What's Changing?

Agent Engine deployment is moving from Python scripts to Terraform for better infrastructure management.

### Benefits You'll Get
- ✅ No more manual AGENT_ENGINE_ID management
- ✅ Automatic state tracking
- ✅ Rollback capabilities
- ✅ Team collaboration via state sharing

### What Stays the Same
- ✅ Local development workflow (`uv run local-agent`)
- ✅ GitHub Actions automation
- ✅ Python agent code
- ✅ Agentspace registration

## Migration Paths

### Path A: Import Existing Agent (Recommended)
Keep your existing agent and bring it under Terraform management.

1. Get your current Agent Engine ID:
   ```bash
   echo $AGENT_ENGINE_ID
   # or check .env file
   ```

2. Import into Terraform:
   ```bash
   cd terraform/deployment
   terraform import google_vertex_ai_reasoning_engine.agent \
     projects/$PROJECT/locations/$LOCATION/reasoningEngines/$AGENT_ENGINE_ID
   ```

3. Verify import:
   ```bash
   terraform plan
   # Should show "No changes"
   ```

### Path B: Fresh Start
Create a new agent with Terraform (previous agent remains).

1. Clear the old ID:
   ```bash
   unset AGENT_ENGINE_ID
   # Remove from .env
   ```

2. Deploy with Terraform:
   ```bash
   uv run terraform-deploy
   ```

3. (Optional) Delete old agent:
   ```bash
   AGENT_ENGINE_ID=old_id uv run delete
   ```

## Compatibility Period

During migration, both methods work:
- `uv run deploy` - Python method (deprecated)
- `uv run terraform-deploy` - Terraform method (recommended)

Python deployment will be removed in version 1.0.0.
```

**`docs/terraform_architecture.md`:**
```markdown
# Terraform Architecture

## Two-Module Design

Our Terraform configuration is split into two modules with different lifecycles:

```
terraform/
├── setup/          # One-time infrastructure (rarely changes)
│   ├── main.tf
│   ├── iam.tf      # Service accounts, roles
│   ├── github.tf   # GitHub secrets/variables
│   └── services.tf # API enablement
│
└── deployment/     # Per-deployment resources (changes with code)
    ├── main.tf
    ├── agent.tf    # Agent Engine resource
    └── data.tf     # References setup outputs
```

## Why Two Modules?

### Single Module Problems
- `terraform destroy` would delete EVERYTHING
- CI/CD infrastructure mixed with application deployments
- Hard to manage different change frequencies

### Two Module Benefits
- Setup infrastructure protected from accidental deletion
- Deployment can be destroyed/recreated safely
- Clear separation of concerns
- Different teams can manage each module

## State Management

Each module has its own Terraform state:

- **Setup State**: Contains service accounts, IAM, GitHub config
- **Deployment State**: Contains Agent Engine instance, configurations

The deployment module reads setup outputs via `terraform_remote_state`.
```

### 4.3 Updated Documentation

**`docs/cicd_setup_github_actions.md`:**
```markdown
# CI/CD Setup with GitHub Actions

## Overview

The CI/CD pipeline now uses Terraform for infrastructure management, eliminating manual configuration steps.

## Setup Process (Simplified!)

### Previous Process (3 Phases)
1. ✅ Phase 1: Run Terraform for infrastructure
2. ❌ Phase 2: Manual - Capture AGENT_ENGINE_ID, update .env, re-run Terraform
3. ✅ Phase 3: Ongoing deployments

### New Process (2 Phases)
1. ✅ Phase 1: Run Terraform for complete infrastructure
2. ✅ Phase 2: Ongoing deployments (fully automated)

**We eliminated the manual phase!** 🎉

## Phase 1: Infrastructure Setup

### Step 1: Setup Base Infrastructure
```bash
cd terraform/setup
terraform init
terraform apply
```

Creates:
- Service accounts (cicd, app)
- IAM roles and bindings
- Workload Identity Federation
- GitHub secrets and variables
- Required APIs

### Step 2: Deploy Agent Engine
```bash
cd ../deployment
terraform init
terraform apply
```

Creates:
- Agent Engine instance
- GCS staging bucket
- Runtime configuration

**Output includes:**
```
agent_engine_id = "1234567890"
agent_url = "https://console.cloud.google.com/..."
```

No manual ID capture needed - Terraform tracks it automatically!

## Phase 2: Ongoing Development

Push code to main branch → GitHub Actions runs → Agent updates automatically

The workflow now runs Terraform instead of Python for deployments.
```

---

## 5. Error Handling & Messaging

### 5.1 Common Failure Scenarios

#### Scenario: Terraform State Conflicts

**Current Error:**
```
Error: Resource already exists
```

**Improved Error:**
```
Error: Agent Engine Already Exists

An Agent Engine named "my-agent" already exists in this project.

Possible solutions:

1. Import existing agent into Terraform:
   terraform import google_vertex_ai_reasoning_engine.agent \
     projects/my-project/locations/us-central1/reasoningEngines/1234567890

2. Use a different name:
   terraform apply -var="agent_display_name=my-agent-v2"

3. Delete existing agent first (destructive!):
   gcloud ai reasoning-engines delete 1234567890 --location=us-central1

Need help? See: docs/troubleshooting.md#existing-resource
```

#### Scenario: Missing Pickle File

**Current Error:**
```
Error: pickle_object_gcs_uri is required
```

**Improved Error:**
```
Error: Agent Package Incomplete

The Terraform deployment requires a pickle file, but none was found.

Quick fixes:

1. Generate pickle file:
   python scripts/create_pickle.py

2. Use Python deployment instead:
   uv run deploy --legacy

Why this happens:
- Terraform needs pre-built artifacts
- Python SDK builds them automatically

For automatic pickle generation, see:
docs/terraform_architecture.md#pickle-generation
```

#### Scenario: State Lock

**Current Error:**
```
Error: Error acquiring the state lock
```

**Improved Error:**
```
Error: Deployment In Progress

Another deployment is currently running or a previous deployment didn't complete cleanly.

Check if deployment is running:
1. Check GitHub Actions: https://github.com/YOUR_REPO/actions
2. Check Terraform processes: ps aux | grep terraform

If no deployment is running, unlock:
terraform force-unlock <LOCK_ID>

To prevent this:
- Don't interrupt Terraform operations
- Use GitHub Actions for deployments (automatic locking)

Details: docs/troubleshooting.md#state-lock
```

### 5.2 Success Confirmations

**After Setup Module:**
```
✅ Infrastructure Setup Complete!

Created resources:
- Service accounts: my-agent-cicd, my-agent-app
- GitHub secrets: Configured for my-repo
- APIs enabled: 7 services
- IAM roles: Configured

Next step: Deploy your agent
  cd ../deployment && terraform apply
```

**After Deployment Module:**
```
✅ Agent Engine Deployed Successfully!

Agent Details:
- ID: 1234567890
- Name: my-agent
- Region: us-central1
- URL: https://console.cloud.google.com/vertex-ai/reasoning-engines/1234567890

Test your agent:
  uv run remote-agent

View logs:
  gcloud ai reasoning-engines logs 1234567890 --location=us-central1
```

**After GitHub Actions Deployment:**
```
✅ Deployment Complete

Changes deployed:
- Wheel version: 0.3.0+gitabc123
- Updated: 2025-10-09 15:24:00 UTC
- Duration: 2m 15s

Agent endpoint:
https://us-central1-aiplatform.googleapis.com/v1/projects/my-project/locations/us-central1/reasoningEngines/1234567890

View in console:
https://console.cloud.google.com/vertex-ai/reasoning-engines/1234567890
```

---

## 6. Backward Compatibility

### 6.1 Impact on Existing Repos

**Compatibility Matrix:**

| Component | Old Method | New Method | Compatible? |
|-----------|------------|------------|-------------|
| Local testing | `uv run local-agent` | Same | ✅ Yes |
| Manual deploy | `uv run deploy` | `uv run terraform-deploy` | ✅ Both work |
| GitHub Actions | Python script | Terraform | ⚠️ Needs update |
| State management | `AGENT_ENGINE_ID` env | Terraform state | ⚠️ Migration needed |
| Agentspace | Python script | Same | ✅ Yes |

### 6.2 Migration Path

**Phase 1: Parallel Support (v0.4.0 - v0.9.x)**
- Both Python and Terraform deployment work
- Documentation shows both methods
- New projects use Terraform by default
- Existing projects can migrate at their pace

**Phase 2: Deprecation (v0.10.0)**
- Python deployment marked deprecated
- Migration guide prominently featured
- Terraform becomes primary method
- Python method shows warnings

**Phase 3: Removal (v1.0.0)**
- Python deployment removed
- Only Terraform method remains
- Clean, simplified codebase

### 6.3 Coexistence Strategy

**Directory Structure Supporting Both:**
```
project/
├── terraform/
│   ├── setup/        # New: Terraform setup
│   ├── deployment/   # New: Terraform deployment
│   └── legacy/       # Old: Monolithic Terraform (deprecated)
├── src/deployment/
│   ├── deploy_agent.py    # Keep for compatibility
│   └── legacy_deploy.py   # Renamed to clarify
└── scripts/
    ├── terraform_wrapper.py  # New: Simplify Terraform
    └── create_pickle.py      # New: Support Terraform
```

**Command Coexistence:**
```python
# pyproject.toml
[project.scripts]
# Legacy commands (show deprecation warning)
deploy = "src.deployment.legacy_deploy:main"

# New commands (recommended)
terraform-setup = "scripts.terraform_wrapper:setup"
terraform-deploy = "scripts.terraform_wrapper:deploy"

# Unchanged commands
local-agent = "src.deployment.run_local_agent:main"
remote-agent = "src.deployment.run_remote_agent:main"
```

---

## 7. Accessibility Considerations

### 7.1 Making Terraform Accessible to Python Developers

**Mental Model Building:**

```markdown
## Understanding Terraform (for Python Developers)

Think of Terraform like this:

Python Class : Instance :: Terraform Resource : Infrastructure

```python
# In Python, you define a class
class AgentEngine:
    def __init__(self, name, region):
        self.name = name
        self.region = region

# Then create instances
my_agent = AgentEngine("production", "us-central1")
```

```hcl
# In Terraform, you define a resource
resource "google_vertex_ai_reasoning_engine" "agent" {
  display_name = "production"
  region       = "us-central1"
}

# Terraform creates the actual infrastructure
```

Key differences:
- Python runs immediately, Terraform plans then applies
- Python uses variables, Terraform uses state files
- Python prints output, Terraform tracks resources
```

### 7.2 Progressive Disclosure of Complexity

**Level 1: Just Commands**
```bash
# What users see initially
uv run terraform-setup    # Setup infrastructure
uv run terraform-deploy   # Deploy agent
```

**Level 2: Understanding Plans**
```bash
# Intermediate users learn about planning
terraform plan   # See what will change
terraform apply  # Make the changes
```

**Level 3: State Management**
```bash
# Advanced users understand state
terraform state list              # See tracked resources
terraform state show <resource>  # Inspect details
terraform import <resource>      # Import existing
```

### 7.3 Clear Visual Feedback

**Use Emojis and Colors:**
```
🔧 Setup Module:
  ├─ ✅ Service accounts created
  ├─ ✅ APIs enabled
  └─ ✅ GitHub configured

🚀 Deployment Module:
  ├─ ⏳ Creating Agent Engine...
  ├─ ✅ Agent Engine created
  └─ ✅ Configuration applied

📊 Summary:
  Agent ID: 1234567890
  Status: Ready
  Next: Push code to deploy updates
```

**Progress Indicators:**
```
Terraform Apply Progress: [████████████████████] 100%
Resources: 5 added, 2 changed, 0 destroyed
Time elapsed: 2m 15s
```

---

## 8. Success Metrics

### 8.1 Developer Experience Metrics

**Time to First Deployment:**
- Current: 90 minutes (including Phase 2 manual step)
- Target: 60 minutes (no manual steps)
- Stretch: 45 minutes (with wrapper scripts)

**Error Recovery Time:**
- Current: 15-30 minutes (debugging ID issues)
- Target: 5 minutes (clear error messages)
- Stretch: 2 minutes (automated fixes)

**Support Tickets:**
- Current issues: "AGENT_ENGINE_ID not working" (40% of tickets)
- Expected: Terraform state questions (20% of tickets)
- Success: <10% deployment-related tickets

### 8.2 Adoption Metrics

**New Projects:**
- Month 1: 50% use Terraform path
- Month 3: 80% use Terraform path
- Month 6: 95% use Terraform path

**Migration from Existing:**
- Month 1: 10% migrate
- Month 3: 40% migrate
- Month 6: 70% migrate

**Command Usage:**
```python
# Track via analytics
{
  "uv run deploy": decreasing,
  "uv run terraform-deploy": increasing,
  "terraform apply": power_users
}
```

---

## 9. Implementation Priorities

### Phase 1: Core Migration (Week 1-2)

**P0 - Critical:**
- [ ] Split Terraform into setup/deployment modules
- [ ] Create `google_vertex_ai_reasoning_engine` resource config
- [ ] Update GitHub Actions workflow
- [ ] Basic error messages

**P1 - Important:**
- [ ] Wrapper scripts for Terraform commands
- [ ] Migration guide documentation
- [ ] Import instructions for existing agents

### Phase 2: Developer Experience (Week 3-4)

**P1 - Important:**
- [ ] Enhanced error messages with solutions
- [ ] Progress indicators in scripts
- [ ] Fallback to Python deployment option
- [ ] README updates with choice architecture

**P2 - Nice to Have:**
- [ ] Interactive setup wizard
- [ ] Terraform plan visualization
- [ ] Rollback procedures

### Phase 3: Polish and Adoption (Week 5-6)

**P2 - Nice to Have:**
- [ ] Video walkthrough of migration
- [ ] Terraform tips for Python developers
- [ ] Advanced customization guides
- [ ] State management best practices

**P3 - Future:**
- [ ] Multiple environment support
- [ ] Remote state backend setup
- [ ] Team collaboration features

---

## 10. Risk Mitigation

### 10.1 Technical Risks

**Risk: Pickle file generation complexity**
- Mitigation: Keep Python deployment as fallback
- Long-term: Investigate wheel-only deployment

**Risk: Terraform state corruption**
- Mitigation: State backups in GCS versioning
- Recovery: Document state recovery procedures

**Risk: Breaking changes for existing users**
- Mitigation: Parallel support period
- Communication: Clear deprecation timeline

### 10.2 Adoption Risks

**Risk: Python developers reject Terraform**
- Mitigation: Wrapper scripts hide complexity
- Education: "Terraform for Python Developers" guide

**Risk: Increased support burden**
- Mitigation: Comprehensive troubleshooting docs
- Proactive: Common issues in FAQ

**Risk: Migration failures**
- Mitigation: Reversible migration process
- Safety: Keep Python method during transition

---

## 11. Summary and Recommendations

### Key Design Decisions

1. **Two-module Terraform architecture** - Separates "setup once" from "deploy repeatedly"
2. **Wrapper scripts** - Hide Terraform complexity from Python developers
3. **Parallel support period** - Both methods work during migration
4. **No manual ID management** - Terraform state handles automatically
5. **Progressive disclosure** - Complexity revealed gradually

### Critical Success Factors

1. **Clear migration path** - Existing users can transition smoothly
2. **Excellent error messages** - Include solutions, not just problems
3. **Preserved local workflow** - Development experience unchanged
4. **Visual feedback** - Progress indicators and confirmations
5. **Escape hatches** - Python fallback when Terraform fails

### Next Steps

1. **Validate with users** - Test migration with 3-5 existing users
2. **Prototype wrapper scripts** - Confirm they simplify experience
3. **Create migration guide** - Step-by-step with screenshots
4. **Update quickstart** - Reflect new workflow
5. **Monitor adoption** - Track metrics and adjust approach

### Success Criteria

The migration succeeds when:
- New users complete deployment without assistance
- Existing users migrate without breaking deployments
- Support tickets decrease by 50%
- 80% of users choose Terraform path
- No one asks about AGENT_ENGINE_ID anymore

---

## Appendix A: User Interview Questions

For validating design decisions:

1. "Walk me through how you currently deploy agents"
2. "What's the most frustrating part of the current process?"
3. "How comfortable are you with infrastructure-as-code?"
4. "What would make you hesitate to migrate to Terraform?"
5. "What information do you need during deployment?"

## Appendix B: Competitive Analysis

How other projects handle similar migrations:

- **Vercel**: Automatic infrastructure, hides complexity completely
- **Netlify**: Progressive disclosure, GUI → CLI → API
- **AWS CDK**: Familiar programming languages for infrastructure
- **Pulumi**: Code-first infrastructure, no DSL learning

Key lesson: **Hide complexity by default, reveal when needed**

## Appendix C: Error Message Templates

Standard format for all error messages:

```
Error: [Brief description]

[Detailed explanation of what went wrong]

Possible solutions:

1. [Most likely fix]
   [Command to run]

2. [Alternative approach]
   [Command to run]

3. [Fallback option]
   [Command to run]

[Link to detailed documentation]
```

This ensures consistency and helpfulness across all errors.