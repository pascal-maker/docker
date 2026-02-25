# Cloud Scheduler: invoke usage_digest daily at 9:00 Europe/Brussels.

resource "google_service_account" "usage_digest_scheduler" {
  project      = var.project_id
  account_id   = "usage-digest-scheduler"
  display_name = "Usage digest scheduler (invokes usage-digest function)"
}

resource "google_cloud_run_v2_service_iam_member" "usage_digest_scheduler_invoker" {
  location = google_cloudfunctions2_function.usage_digest.location
  name     = google_cloudfunctions2_function.usage_digest.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.usage_digest_scheduler.email}"
}

resource "google_cloud_scheduler_job" "usage_digest" {
  name        = "usage-digest-daily"
  project     = var.project_id
  region      = var.region
  description = "Invoke usage-digest Cloud Function daily"

  schedule = "0 9 * * *"
  time_zone = "Europe/Brussels"

  http_target {
    uri         = "https://${var.region}-${var.project_id}.cloudfunctions.net/usage-digest"
    http_method = "POST"
    oidc_token {
      service_account_email = google_service_account.usage_digest_scheduler.email
      audience              = "https://${var.region}-${var.project_id}.cloudfunctions.net/usage-digest"
    }
  }

  depends_on = [
    google_cloudfunctions2_function.usage_digest,
    google_cloud_run_v2_service_iam_member.usage_digest_scheduler_invoker,
  ]
}
