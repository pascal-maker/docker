# Cloud Run service for the A2A refactor server (EU-only, europe-west1).
# Build and push the image first; set var.a2a_image to the full image URL.

data "google_project" "project" {
  project_id = var.project_id
}

# Grant default Cloud Run SA access to the Anthropic API key secret.
resource "google_secret_manager_secret_iam_member" "anthropic_key_cloudrun" {
  secret_id = google_secret_manager_secret.anthropic_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member   = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

resource "google_cloud_run_v2_service" "a2a" {
  name     = "a2a-server"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = var.a2a_min_instance_count
      max_instance_count = 1
    }
    containers {
      image   = var.a2a_image
      command = ["sh", "docker/entrypoint-cloudrun.sh"]
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.anthropic_api_key.name
            version = "latest"
          }
        }
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = false
      }
    }
  }

  depends_on = [
    google_project_service.run,
    google_secret_manager_secret_iam_member.anthropic_key_cloudrun,
  ]
}

# Allow unauthenticated invocations (dev only; restrict with IAM for production).
resource "google_cloud_run_v2_service_iam_member" "a2a_public" {
  location = google_cloud_run_v2_service.a2a.location
  name     = google_cloud_run_v2_service.a2a.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
