# Cloud Run service for the A2A refactor server (EU-only, europe-west1).
# Build and push the image first; set var.a2a_image to the full image URL.

# Grant default Cloud Run SA access to the Anthropic API key secret.
resource "google_secret_manager_secret_iam_member" "anthropic_key_cloudrun" {
  secret_id = "projects/${var.project_id}/secrets/refactor-agent-anthropic-api-key"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

# Grant Cloud Run SA access to Firestore for user store, audit log, rate limits.
resource "google_project_iam_member" "cloudrun_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
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
            secret  = var.anthropic_api_key_secret_name
            version = "latest"
          }
        }
      }
      env {
        name  = "ONBOARDING_MODE"
        value = "alpha"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "REPLICA_DIR"
        value = "/tmp/replica"
      }
      env {
        name  = "REPLICA_TTL_MINUTES"
        value = "30"
      }
      env {
        name  = "SENTRY_DSN"
        value = var.sentry_dsn_backend
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
