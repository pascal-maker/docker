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
  description = "GCS bucket name for Terraform state (e.g. PROJECT-terraform-state). If set, GitHub Actions SA gets storage.admin so CI can run terraform apply and manage bucket IAM."
  type        = string
  default     = ""
}

# Sentry (optional). Set SENTRY_AUTH_TOKEN env or sentry_auth_token in secrets.tfvars.
variable "sentry_auth_token" {
  description = "Sentry auth token for Terraform provider. Create at sentry.io: Settings → Auth Tokens (scopes: project:read, project:write, org:read, team:read, team:write)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "sentry_organization" {
  description = "Sentry organization slug (e.g. my-org). Required when using Sentry IaC."
  type        = string
  default     = ""
}

variable "sentry_base_url" {
  description = "Sentry API base URL. Use https://de.sentry.io/api/ for EU region; default is US (sentry.io)."
  type        = string
  default     = ""
}

# Cloudflare (optional). Set when using cloudflare module for DNS and Email Routing.
variable "cloudflare_api_token" {
  description = "Cloudflare API token (Zone:DNS Edit, Email Routing:Edit). Set in secrets.tfvars when using cloudflare module."
  type        = string
  default     = ""
  sensitive   = true
}

variable "cloudflare_email_destination" {
  description = "Real email that receives forwards from noreply@ and admin@refactorum.com. Must verify once via Cloudflare link."
  type        = string
  default     = ""
  sensitive   = true
}

# Resend DNS (add domain in Resend Dashboard first, then add values here).
variable "resend_dkim_name" {
  description = "Resend DKIM record name (e.g. resend._domainkey). From Resend Dashboard after adding domain."
  type        = string
  default     = ""
}

variable "resend_dkim_target" {
  description = "Resend DKIM value: CNAME target hostname or TXT content (p=...). See resend_dkim_type."
  type        = string
  default     = ""
}

variable "resend_dkim_type" {
  description = "Resend DKIM record type: CNAME (target hostname) or TXT (p=... key). Resend Domains shows which."
  type        = string
  default     = "CNAME"
}

# Firebase Hosting custom domains (Terraform-managed). When set, registers each domain in Firebase
# and creates DNS records in Cloudflare from Firebase's required_dns_updates. Empty to use
# manual firebase_hosting_* variables instead.
variable "firebase_custom_domains" {
  description = "Custom domains for Firebase Hosting (e.g. [\"refactorum.com\", \"www.refactorum.com\"]). Terraform registers each and creates DNS."
  type        = list(string)
  default     = []
}

# Firebase Hosting DNS (manual fallback when firebase_custom_domain is empty).
variable "firebase_hosting_target" {
  description = "Firebase Hosting A/CNAME target for root or www. From Firebase Console after adding custom domain."
  type        = string
  default     = ""
}

variable "firebase_hosting_type" {
  description = "Firebase Hosting record type: A or CNAME."
  type        = string
  default     = "CNAME"
}

variable "firebase_hosting_name" {
  description = "Firebase Hosting DNS record name: @ for root, www for www subdomain."
  type        = string
  default     = "www"
}

# Site: marketing site and auth flow.
variable "site_url" {
  description = "Full URL of the marketing site (e.g. https://refactorum.com)."
  type        = string
  default     = "https://refactorum.com"
}

variable "site_admin_email" {
  description = "Admin email for access request notifications (e.g. admin@refactorum.com)."
  type        = string
  default     = "admin@refactorum.com"
}

variable "github_oauth_client_id" {
  description = "Deprecated: GitHub OAuth App Client ID. Use github_app_client_id."
  type        = string
  default     = ""
}

variable "github_oauth_client_secret" {
  description = "Deprecated: GitHub OAuth App Client secret. Use github_app_*."
  type        = string
  default     = ""
  sensitive   = true
}

# GitHub App (replaces OAuth App for per-repo access).
variable "github_app_id" {
  description = "GitHub App ID (numeric). Set in secrets.tfvars. From GitHub App settings."
  type        = string
  default     = ""
}

variable "github_app_client_id" {
  description = "GitHub App Client ID. Set in secrets.tfvars. From GitHub App settings."
  type        = string
  default     = ""
}

variable "github_app_client_secret" {
  description = "GitHub App Client secret. Set in secrets.tfvars. Required for auth callback."
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_app_private_key" {
  description = "GitHub App private key (PEM content). Set in secrets.tfvars. Alternative: use github_app_private_key_path."
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_app_private_key_path" {
  description = "Path to GitHub App private key PEM file (relative to infra/). Use when you prefer not to put PEM in tfvars."
  type        = string
  default     = ""
}

variable "github_app_webhook_secret" {
  description = "GitHub App webhook secret. Set in secrets.tfvars. For webhook signature verification."
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

# GitHub provider for Terraform-managed Actions secrets.
variable "github_token" {
  description = "GitHub fine-grained PAT for managing Actions secrets. Set in secrets.tfvars."
  type        = string
  default     = ""
  sensitive   = true
}

variable "github_repository" {
  description = "GitHub repository (owner/name, e.g. my-org/refactor-agent). Required for Terraform-managed Actions secrets."
  type        = string
  default     = ""
}

variable "firebase_service_account_json" {
  description = "Firebase service account JSON for deploy-site workflow. Set in secrets.tfvars. Terraform syncs to GitHub secret FIREBASE_SERVICE_ACCOUNT."
  type        = string
  default     = ""
  sensitive   = true
}

variable "nx_cloud_access_token" {
  description = "Nx Cloud CI access token for remote cache. Create via 'nx connect' or Nx Cloud dashboard. Terraform syncs to GitHub secret NX_CLOUD_ACCESS_TOKEN."
  type        = string
  default     = ""
  sensitive   = true
}

# GDPR / legal (Belgium). Terraform syncs to GitHub Actions variables for site build.
variable "vite_imprint_name" {
  description = "Imprint name (Belgium legal notice). Synced to VITE_IMPRINT_NAME for site build."
  type        = string
  default     = ""
}

variable "vite_imprint_email" {
  description = "Imprint contact email. Synced to VITE_IMPRINT_EMAIL for site build."
  type        = string
  default     = ""
}

variable "vite_privacy_policy_url" {
  description = "URL to hosted privacy policy (e.g. Termly/iubenda). Synced to VITE_PRIVACY_POLICY_URL."
  type        = string
  default     = ""
}

variable "vite_terms_url" {
  description = "URL to hosted terms of service. Synced to VITE_TERMS_URL."
  type        = string
  default     = ""
}

variable "vite_firebase_measurement_id" {
  description = "Firebase Analytics measurement ID (consent-gated). Synced to VITE_FIREBASE_MEASUREMENT_ID."
  type        = string
  default     = ""
}

