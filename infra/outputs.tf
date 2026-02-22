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
