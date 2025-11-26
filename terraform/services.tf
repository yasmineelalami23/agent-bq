locals {
  services = [
    "aiplatform.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "discoveryengine.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "telemetry.googleapis.com",
  ]
}

resource "google_project_service" "main" {
  for_each           = toset(local.services)
  project            = local.project_id
  service            = each.value
  disable_on_destroy = false
}
