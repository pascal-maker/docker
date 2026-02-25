# Cloud Run service for the Chainlit UI (transparent surface, highly secured).
# Deploy only when chainlit_image is set; use IAM to restrict invoker (no allUsers).

resource "google_secret_manager_secret_iam_member" "chainlit_auth_cloudrun" {
  count     = var.chainlit_image != "" ? 1 : 0
  secret_id = "projects/${var.project_id}/secrets/refactor-agent-chainlit-auth-secret"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

resource "google_cloud_run_v2_service" "chainlit" {
  count    = var.chainlit_image != "" ? 1 : 0
  name     = "chainlit-ui"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    containers {
      image   = var.chainlit_image
      command = ["sh", "docker/entrypoint-chainlit.sh"]
      env {
        name  = "REFACTOR_AGENT_A2A_URL"
        value = var.a2a_url
      }
      env {
        name = "CHAINLIT_AUTH_SECRET"
        value_source {
          secret_key_ref {
            secret  = var.chainlit_auth_secret_name
            version = "latest"
          }
        }
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
    google_secret_manager_secret_iam_member.chainlit_auth_cloudrun,
  ]
}

# Restrict Chainlit to the specified IAM member(s); do not use allUsers.
resource "google_cloud_run_v2_service_iam_member" "chainlit_invoker" {
  count    = var.chainlit_image != "" && var.chainlit_invoker_member != "" ? 1 : 0
  location = google_cloud_run_v2_service.chainlit[0].location
  name     = google_cloud_run_v2_service.chainlit[0].name
  role     = "roles/run.invoker"
  member   = var.chainlit_invoker_member
}
