# Cloud Run service for the Chainlit UI (transparent surface, highly secured).
# Deploy only when chainlit_image is set; use IAM to restrict invoker (no allUsers).

resource "google_secret_manager_secret_iam_member" "chainlit_auth_cloudrun" {
  count     = var.chainlit_image != "" ? 1 : 0
  secret_id = google_secret_manager_secret.chainlit_auth_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
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
        value = google_cloud_run_v2_service.a2a.uri
      }
      env {
        name = "CHAINLIT_AUTH_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.chainlit_auth_secret.name
            version = "latest"
          }
        }
      }
      env {
        name  = "SENTRY_DSN"
        value = try(sentry_key.backend[0].dsn["public"], "")
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
