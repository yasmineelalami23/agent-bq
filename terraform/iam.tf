locals {
  app_iam_roles = [
    "roles/aiplatform.user",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
    "roles/telemetry.tracesWriter",
    "roles/serviceusage.serviceUsageConsumer",
  ]
  cicd_iam_roles = [
    "roles/aiplatform.user",
    "roles/discoveryengine.editor",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/storage.admin",
  ]
  github_workload_iam_roles = [
    "roles/iam.workloadIdentityUser",
  ]
}

resource "google_service_account" "cicd" {
  account_id   = "${local.agent_name}-cicd"
  display_name = "${local.agent_name} CICD Runner Service Account"
}

resource "google_service_account" "app" {
  account_id   = "${local.agent_name}-app"
  display_name = "${local.agent_name} App Service Account"
}

resource "google_project_iam_member" "cicd" {
  for_each = toset(local.cicd_iam_roles)
  project  = local.project_id
  role     = each.value
  member   = google_service_account.cicd.member
}

resource "google_project_iam_member" "app" {
  for_each = toset(local.app_iam_roles)
  project  = local.project_id
  role     = each.value
  member   = google_service_account.app.member
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "${local.agent_name}-github"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_provider_id = "${local.agent_name}-oidc"
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  display_name                       = "GitHub OIDC"
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }
  attribute_condition = "attribute.repository == '${local.repository_owner}/${local.repository_name}'"
}

resource "google_service_account_iam_member" "github_workload" {
  for_each           = toset(local.github_workload_iam_roles)
  service_account_id = google_service_account.cicd.name
  role               = each.value
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${local.repository_owner}/${local.repository_name}"
}
