variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region (europe-west1)."
  type        = string
}

variable "a2a_image" {
  description = "Full Docker image URL for the A2A server."
  type        = string
}

variable "a2a_min_instance_count" {
  description = "Minimum number of A2A Cloud Run instances (0 = scale to zero; 1 = always-on for staging)."
  type        = number
  default     = 0
}

variable "anthropic_api_key_secret_name" {
  description = "Secret Manager secret name for Anthropic API key."
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
