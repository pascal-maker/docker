# GitHub Actions secrets and variables managed by Terraform.
# Requires: github_token, github_repository (owner/repo) in tfvars.
# Token: fine-grained PAT with Repository permissions:
#   Secrets (Read and write), Variables (Read and write), Administration (Read and write).
# Syncs GCP_PROJECT_ID (variable), VITE_GITHUB_OAUTH_CLIENT_ID, VITE_AUTH_CALLBACK_URL,
# FIREBASE_SERVICE_ACCOUNT for site build/deploy.
# Firebase Measurement ID: auto from Terraform-created web app, or override via vite_firebase_measurement_id.

locals {
  firebase_measurement_id = coalesce(var.vite_firebase_measurement_id, module.site.firebase_measurement_id)
  github_repo_name        = try(split("/", var.github_repository)[1], var.github_repository)
}

resource "github_actions_variable" "gcp_project_id" {
  count         = var.github_repository != "" && var.github_token != "" ? 1 : 0
  repository    = local.github_repo_name
  variable_name = "GCP_PROJECT_ID"
  value         = var.project_id
}

# Enable Dependabot security updates (auto-PRs for vulnerable deps). Alerts require dependency graph,
# which is enabled automatically when Dependabot is enabled. dependabot.yml configures ecosystems.
resource "github_repository_dependabot_security_updates" "main" {
  count      = var.github_repository != "" && var.github_token != "" ? 1 : 0
  repository = local.github_repo_name
  enabled    = true
}

resource "github_actions_secret" "firebase_service_account" {
  count           = var.github_repository != "" && var.github_token != "" && var.firebase_service_account_json != "" ? 1 : 0
  repository      = local.github_repo_name
  secret_name     = "FIREBASE_SERVICE_ACCOUNT"
  plaintext_value = var.firebase_service_account_json
}

resource "github_actions_secret" "vite_github_oauth_client_id" {
  count           = var.github_repository != "" && var.github_token != "" && var.github_oauth_client_id != "" ? 1 : 0
  repository      = local.github_repo_name
  secret_name     = "VITE_GITHUB_OAUTH_CLIENT_ID"
  plaintext_value = var.github_oauth_client_id
}

resource "github_actions_secret" "vite_github_app_client_id" {
  count           = var.github_repository != "" && var.github_token != "" && var.github_app_client_id != "" ? 1 : 0
  repository      = local.github_repo_name
  secret_name     = "VITE_GITHUB_APP_CLIENT_ID"
  plaintext_value = var.github_app_client_id
}

resource "github_actions_secret" "vite_auth_callback_url" {
  count           = var.github_repository != "" && var.github_token != "" ? 1 : 0
  repository      = local.github_repo_name
  secret_name     = "VITE_AUTH_CALLBACK_URL"
  plaintext_value = module.site.auth_callback_url
}

resource "github_actions_secret" "nx_cloud_access_token" {
  count           = var.github_repository != "" && var.github_token != "" && var.nx_cloud_access_token != "" ? 1 : 0
  repository      = local.github_repo_name
  secret_name     = "NX_CLOUD_ACCESS_TOKEN"
  plaintext_value = var.nx_cloud_access_token
}

# GDPR / legal (Belgium). Synced as variables for site build (non-sensitive; baked into client bundle).
resource "github_actions_variable" "vite_imprint_name" {
  count         = var.github_repository != "" && var.github_token != "" && var.vite_imprint_name != "" ? 1 : 0
  repository    = local.github_repo_name
  variable_name = "VITE_IMPRINT_NAME"
  value         = var.vite_imprint_name
}

resource "github_actions_variable" "vite_imprint_email" {
  count         = var.github_repository != "" && var.github_token != "" && var.vite_imprint_email != "" ? 1 : 0
  repository    = local.github_repo_name
  variable_name = "VITE_IMPRINT_EMAIL"
  value         = var.vite_imprint_email
}

resource "github_actions_variable" "vite_privacy_policy_url" {
  count         = var.github_repository != "" && var.github_token != "" && var.vite_privacy_policy_url != "" ? 1 : 0
  repository    = local.github_repo_name
  variable_name = "VITE_PRIVACY_POLICY_URL"
  value         = var.vite_privacy_policy_url
}

resource "github_actions_variable" "vite_terms_url" {
  count         = var.github_repository != "" && var.github_token != "" && var.vite_terms_url != "" ? 1 : 0
  repository    = local.github_repo_name
  variable_name = "VITE_TERMS_URL"
  value         = var.vite_terms_url
}

resource "github_actions_variable" "vite_firebase_measurement_id" {
  count         = var.github_repository != "" && var.github_token != "" && local.firebase_measurement_id != "" ? 1 : 0
  repository    = local.github_repo_name
  variable_name = "VITE_FIREBASE_MEASUREMENT_ID"
  value         = local.firebase_measurement_id
}
