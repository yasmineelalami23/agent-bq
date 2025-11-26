provider "google" {
  project = local.project_id
}

provider "github" {
  owner = local.repository_owner
}

provider "dotenv" {}
