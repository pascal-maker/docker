output "anthropic_api_key_secret_id" {
  description = "Secret Manager secret ID for Anthropic API key."
  value       = google_secret_manager_secret.anthropic_api_key.secret_id
}

output "anthropic_api_key_secret_name" {
  description = "Secret Manager secret name for Anthropic API key."
  value       = google_secret_manager_secret.anthropic_api_key.name
}

output "chainlit_auth_secret_id" {
  description = "Secret Manager secret ID for Chainlit auth."
  value       = google_secret_manager_secret.chainlit_auth_secret.secret_id
}

output "chainlit_auth_secret_name" {
  description = "Secret Manager secret name for Chainlit auth."
  value       = google_secret_manager_secret.chainlit_auth_secret.name
}

output "github_oauth_client_secret_name" {
  description = "Secret Manager secret name for GitHub OAuth client secret."
  value       = google_secret_manager_secret.github_oauth_client_secret.name
}

output "resend_api_key_secret_name" {
  description = "Secret Manager secret name for Resend API key."
  value       = google_secret_manager_secret.resend_api_key.name
}

output "github_actions_sa_email" {
  description = "Service account email for GitHub Actions; use with gcloud iam service-accounts keys create to create a key, then add the JSON to repo secret GCP_SA_KEY."
  value       = google_service_account.github_actions.email
}

output "project_number" {
  description = "GCP project number."
  value       = data.google_project.project.number
}

output "run_service" {
  description = "Cloud Run API service (for depends_on)."
  value       = google_project_service.run
}

output "artifact_registry_repository_id" {
  description = "Artifact Registry repository ID."
  value       = google_artifact_registry_repository.refactor_agent.repository_id
}

output "sentry_dsn_backend" {
  description = "Sentry DSN for backend (Python). Use for SENTRY_DSN env in A2A/Chainlit."
  value       = try(sentry_key.backend[0].dsn["public"], "")
  sensitive   = true
}

output "sentry_dsn_frontend" {
  description = "Sentry DSN for frontend (React). Use for VITE_SENTRY_DSN at build time."
  value       = try(sentry_key.frontend[0].dsn["public"], "")
  sensitive   = true
}

output "sentry_dsn_vscode" {
  description = "Sentry DSN for VS Code extension."
  value       = try(sentry_key.vscode[0].dsn["public"], "")
  sensitive   = true
}
