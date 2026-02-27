output "a2a_url" {
  description = "URL of the deployed A2A Cloud Run service."
  value       = module.a2a.a2a_url
}

output "project_id" {
  description = "GCP project ID."
  value       = var.project_id
}

output "ar_repo" {
  description = "Artifact Registry repository name (for building and pushing images)."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${module.shared.artifact_registry_repository_id}"
}

output "chainlit_url" {
  description = "URL of the Chainlit Cloud Run service (empty when chainlit_image is not set)."
  value       = module.chainlit.chainlit_url
}

# Sentry DSNs (empty when sentry_organization is not set).
output "sentry_dsn_backend" {
  description = "Sentry DSN for backend (Python). Use for SENTRY_DSN env in A2A/Chainlit."
  value       = module.shared.sentry_dsn_backend
  sensitive   = true
}

output "sentry_dsn_frontend" {
  description = "Sentry DSN for frontend (React). Use for VITE_SENTRY_DSN at build time."
  value       = module.shared.sentry_dsn_frontend
  sensitive   = true
}

output "sentry_dsn_vscode" {
  description = "Sentry DSN for VS Code extension."
  value       = module.shared.sentry_dsn_vscode
  sensitive   = true
}

output "github_actions_sa_email" {
  description = "Service account email for GitHub Actions."
  value       = module.shared.github_actions_sa_email
}

output "auth_callback_url" {
  description = "GitHub OAuth callback URL. Set in GitHub OAuth App settings."
  value       = module.site.auth_callback_url
}

output "github_webhook_url" {
  description = "GitHub App webhook URL. Set in GitHub App → Webhook settings."
  value       = module.site.github_webhook_url
}

output "auth_register_device_url" {
  description = "Auth register device URL. Used by extension for device flow."
  value       = module.site.auth_register_device_url
}
