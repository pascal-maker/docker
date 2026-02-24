output "a2a_url" {
  description = "URL of the deployed A2A Cloud Run service."
  value       = google_cloud_run_v2_service.a2a.uri
}

output "project_id" {
  description = "GCP project ID."
  value       = var.project_id
}

output "ar_repo" {
  description = "Artifact Registry repository name (for building and pushing images)."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.refactor_agent.repository_id}"
}

output "chainlit_url" {
  description = "URL of the Chainlit Cloud Run service (empty when chainlit_image is not set)."
  value       = var.chainlit_image != "" ? google_cloud_run_v2_service.chainlit[0].uri : ""
}

# Sentry DSNs (empty when sentry_organization is not set).
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
