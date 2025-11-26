data "dotenv" "adk" {
  filename = "${path.module}/../.env"
}

# Get required Terraform variables from the project .env file unless explicitly passes as a root module input
locals {
  agent_name       = coalesce(var.agent_name, data.dotenv.adk.entries.AGENT_NAME)
  project_id       = coalesce(var.project_id, data.dotenv.adk.entries.GOOGLE_CLOUD_PROJECT)
  repository_name  = coalesce(var.repository_name, data.dotenv.adk.entries.GITHUB_REPO_NAME)
  repository_owner = coalesce(var.repository_owner, data.dotenv.adk.entries.GITHUB_REPO_OWNER)
}
