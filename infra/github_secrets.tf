# GitHub Actions secrets and repository settings managed by Terraform.
# Requires: github_token (admin:repo), github_repository (owner/repo) in tfvars.
# Syncs VITE_GITHUB_OAUTH_CLIENT_ID, VITE_AUTH_CALLBACK_URL, FIREBASE_SERVICE_ACCOUNT for site build/deploy.

# Enable Dependabot security updates (auto-PRs for vulnerable deps). Alerts require dependency graph,
# which is enabled automatically when Dependabot is enabled. dependabot.yml configures ecosystems.
resource "github_repository_dependabot_security_updates" "main" {
  count      = var.github_repository != "" && var.github_token != "" ? 1 : 0
  repository = var.github_repository
  enabled    = true
}

resource "github_actions_secret" "firebase_service_account" {
  count           = var.github_repository != "" && var.github_token != "" && var.firebase_service_account_json != "" ? 1 : 0
  repository      = var.github_repository
  secret_name     = "FIREBASE_SERVICE_ACCOUNT"
  plaintext_value = var.firebase_service_account_json
}

resource "github_actions_secret" "vite_github_oauth_client_id" {
  count           = var.github_repository != "" && var.github_token != "" ? 1 : 0
  repository      = var.github_repository
  secret_name     = "VITE_GITHUB_OAUTH_CLIENT_ID"
  plaintext_value = var.github_oauth_client_id
}

resource "github_actions_secret" "vite_auth_callback_url" {
  count           = var.github_repository != "" && var.github_token != "" ? 1 : 0
  repository      = var.github_repository
  secret_name     = "VITE_AUTH_CALLBACK_URL"
  plaintext_value = module.site.auth_callback_url
}
