variable "project_id" {
  description = "GCP project ID (billing enabled for free-tier usage)."
  type        = string
}

variable "region" {
  description = "GCP region (europe-west1 = Belgium, closest to Ghent; EU-only for GDPR)."
  type        = string
  default     = "europe-west1"
}

variable "anthropic_api_key" {
  description = "Anthropic API key for the A2A server. Set in secrets.tfvars (do not commit)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "chainlit_auth_secret" {
  description = "Chainlit auth secret for hosted Dev UI. Set in secrets.tfvars when deploying Chainlit."
  type        = string
  default     = ""
  sensitive   = true
}

variable "terraform_state_bucket" {
  description = "GCS bucket name for Terraform state (e.g. PROJECT-terraform-state). If set, GitHub Actions SA gets storage.admin so CI can run terraform apply and manage bucket IAM."
  type        = string
  default     = ""
}

variable "github_oauth_client_secret" {
  description = "Deprecated: GitHub OAuth App Client secret. Use github_app_client_secret."
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_app_client_secret" {
  description = "GitHub App Client secret. Set in secrets.tfvars for auth callback Cloud Function."
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_app_private_key" {
  description = "GitHub App private key (PEM). For webhook verification and token refresh."
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_app_webhook_secret" {
  description = "GitHub App webhook secret. For webhook signature verification."
  type        = string
  default     = ""
  sensitive   = true
}

variable "resend_api_key" {
  description = "Resend API key for admin email notifications. Set in secrets.tfvars."
  type        = string
  default     = ""
  sensitive   = true
}

variable "sentry_organization" {
  description = "Sentry organization slug (e.g. my-org). Required when using Sentry IaC."
  type        = string
  default     = ""
}
