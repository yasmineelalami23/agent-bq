locals {
  github_secrets = {
    GCP_WORKLOAD_IDENTITY_PROVIDER = google_iam_workload_identity_pool_provider.github.name
    GCP_SERVICE_ACCOUNT            = google_service_account.cicd.email
  }

  required_keys = toset([
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_CLOUD_STORAGE_BUCKET",
    "AGENT_NAME",
  ])

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

  # Validation: Check that all required keys exist in the .env file and are non-empty
  missing_required_keys = [
    for key in local.required_keys :
    key if !contains(keys(data.dotenv.adk.entries), key) || data.dotenv.adk.entries[key] == ""
  ]

  # Extract keys from the .env file that match one of all_workflow_keys and have a non-empty value
  github_variables = {
    for key in keys(data.dotenv.adk.entries) :
    key => data.dotenv.adk.entries[key]
    if contains(local.all_workflow_keys, key) && data.dotenv.adk.entries[key] != ""
  }
}

# Run the validation check - https://developer.hashicorp.com/terraform/language/validate#checks
check "required_env_vars" {
  assert {
    condition     = length(local.missing_required_keys) == 0
    error_message = "Missing required environment variables in .env file:\n\n${join("\n", local.missing_required_keys)}"
  }
}

resource "github_actions_secret" "secret" {
  for_each        = local.github_secrets
  repository      = local.repository_name
  secret_name     = each.key
  plaintext_value = each.value
}

resource "github_actions_variable" "variable" {
  for_each      = local.github_variables
  repository    = local.repository_name
  variable_name = each.key
  value         = each.value
}
