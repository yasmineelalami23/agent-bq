variable "agent_name" {
  type        = string
  description = "Agent name used to name Terraform resources"
  nullable    = true
  default     = null
}

variable "project_id" {
  type        = string
  description = "Google Cloud project ID"
  nullable    = true
  default     = null
}

variable "repository_name" {
  description = "GitHub repository name"
  type        = string
  nullable    = true
  default     = null
}

variable "repository_owner" {
  description = "GitHub repository owner - username or organization"
  type        = string
  nullable    = true
  default     = null
}
