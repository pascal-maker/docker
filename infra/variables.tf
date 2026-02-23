variable "project_id" {
  description = "GCP project ID (billing enabled for free-tier usage)."
  type        = string
}

variable "region" {
  description = "GCP region (europe-west1 = Belgium, closest to Ghent; EU-only for GDPR)."
  type        = string
  default     = "europe-west1"
}

variable "a2a_image" {
  description = "Full Docker image URL for the A2A server (e.g. europe-west1-docker.pkg.dev/PROJECT/refactor-agent/a2a-server:latest). Build and push before apply."
  type        = string
}

variable "a2a_min_instance_count" {
  description = "Minimum number of A2A Cloud Run instances (0 = scale to zero; 1 = always-on for staging to avoid cold start)."
  type        = number
  default     = 0
}

variable "chainlit_image" {
  description = "Full Docker image URL for the Chainlit UI (e.g. europe-west1-docker.pkg.dev/PROJECT/refactor-agent/chainlit-ui:staging). Same image as A2A with command overridden to entrypoint-chainlit.sh."
  type        = string
  default     = ""
}

variable "chainlit_invoker_member" {
  description = "IAM member allowed to invoke the Chainlit service (e.g. user:you@example.com). Leave empty to skip granting invoker (deploy only)."
  type        = string
  default     = ""
}

# Provider / app secrets. Set via secrets.tfvars (gitignored) or TF_VAR_* env.
# Changing a key: update secrets.tfvars and terraform apply. Adding a provider: add variable + secret version below.
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

# Optional: used to grant GitHub Actions SA access to Terraform state bucket for CI deploy.
variable "terraform_state_bucket" {
  description = "GCS bucket name for Terraform state (e.g. PROJECT-terraform-state). If set, GitHub Actions SA gets objectAdmin so CI can run terraform apply."
  type        = string
  default     = ""
}
