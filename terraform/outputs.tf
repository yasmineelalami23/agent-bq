output "agent_name" {
  description = "Agent name used to name Terraform resources"
  value       = local.agent_name
}

output "project_id" {
  description = "Google Cloud project ID"
  value       = local.project_id
}

output "enabled_services" {
  description = "List of enabled Google Cloud services"
  value       = [for service in google_project_service.main : service.service]
}

output "app_service_account_email" {
  description = "Email address of the App service account"
  value       = google_service_account.app.email
}

output "cicd_service_account_email" {
  description = "Email address of the CICD service account"
  value       = google_service_account.cicd.email
}

output "workload_identity_provider_name" {
  description = "Full name of the workload identity provider for GitHub Actions"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "repository_full_name" {
  description = "Full GitHub repository name (owner/repo)"
  value       = "${local.repository_owner}/${local.repository_name}"
}

output "github_secrets_configured" {
  description = "List of GitHub secrets configured"
  value       = keys(local.github_secrets)
}

output "github_variables_configured" {
  description = "List of GitHub variables configured"
  value       = keys(local.github_variables)
}
