variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region (europe-west1)."
  type        = string
}

variable "chainlit_image" {
  description = "Full Docker image URL for the Chainlit UI."
  type        = string
  default     = ""
}

variable "chainlit_invoker_member" {
  description = "IAM member allowed to invoke the Chainlit service (e.g. user:you@example.com). Leave empty to skip granting invoker."
  type        = string
  default     = ""
}

variable "chainlit_auth_secret_name" {
  description = "Secret Manager secret name for Chainlit auth."
  type        = string
}

variable "a2a_url" {
  description = "URL of the A2A Cloud Run service."
  type        = string
}

variable "project_number" {
  description = "GCP project number."
  type        = string
}

variable "sentry_dsn_backend" {
  description = "Sentry DSN for backend (optional)."
  type        = string
  default     = ""
  sensitive   = true
}
