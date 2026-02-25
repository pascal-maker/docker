variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "project_number" {
  description = "GCP project number (for Cloud Run secret annotations)."
  type        = string
}

variable "region" {
  description = "GCP region (europe-west1)."
  type        = string
}

variable "site_url" {
  description = "Full URL of the marketing site (e.g. https://refactorum.com)."
  type        = string
}

variable "github_oauth_client_secret_name" {
  description = "Secret Manager secret name for GitHub OAuth client secret."
  type        = string
}

variable "resend_api_key_secret_name" {
  description = "Secret Manager secret name for Resend API key."
  type        = string
}

variable "admin_email" {
  description = "Admin email for access request notifications."
  type        = string
}

variable "github_oauth_client_id" {
  description = "GitHub OAuth App Client ID (from GitHub Developer Settings)."
  type        = string
}
