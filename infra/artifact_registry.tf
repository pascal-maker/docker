# Artifact Registry repository for Docker images (A2A server, later dashboard).
# Location is var.region (europe-west1) so images stay in the EU (GDPR).

resource "google_artifact_registry_repository" "refactor_agent" {
  project       = var.project_id
  location      = var.region
  repository_id = "refactor-agent"
  description   = "Docker images for refactor-agent (A2A server, dashboard)."
  format        = "DOCKER"
  depends_on    = [google_project_service.artifactregistry]
}
