# Grant default Cloud Run/Cloud Functions SA access to secrets and Eventarc for site Cloud Functions.
# Cloud Functions Gen2 uses PROJECT_NUMBER-compute@developer.gserviceaccount.com by default.
resource "google_secret_manager_secret_iam_member" "github_oauth_cloudrun" {
  count     = length(var.github_oauth_client_secret_name) > 0 ? 1 : 0
  secret_id = "projects/${var.project_id}/secrets/${var.github_oauth_client_secret_name}"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "github_app_client_secret_cloudrun" {
  secret_id = "projects/${var.project_id}/secrets/${var.github_app_client_secret_name}"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "github_app_private_key_cloudrun" {
  secret_id = "projects/${var.project_id}/secrets/${var.github_app_private_key_secret_name}"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "github_app_webhook_secret_cloudrun" {
  secret_id = "projects/${var.project_id}/secrets/${var.github_app_webhook_secret_name}"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "resend_api_key_cloudrun" {
  secret_id = "projects/${var.project_id}/secrets/refactor-agent-resend-api-key"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

# Eventarc Firestore trigger: default compute SA must receive events (eventarc.events.receiveEvent).
resource "google_project_iam_member" "eventarc_event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

# Usage digest: default compute SA must read Cloud Monitoring metrics.
resource "google_project_iam_member" "usage_digest_monitoring_reader" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}
