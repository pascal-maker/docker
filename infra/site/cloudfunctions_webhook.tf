# GitHub webhook Cloud Function: installation_repositories -> sync allowed_repos in Firestore.
# TypeScript (nodejs24). Run `make functions-build` before terraform apply.

data "archive_file" "github_webhook" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/github_webhook/.deploy"
  output_path = "${path.module}/.build/github_webhook.zip"
}

resource "google_storage_bucket_object" "github_webhook" {
  name   = "github_webhook-${data.archive_file.github_webhook.output_md5}.zip"
  bucket = google_storage_bucket.functions_source.name
  source = data.archive_file.github_webhook.output_path
}

resource "google_cloudfunctions2_function" "github_webhook" {
  name     = "github-webhook"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "nodejs24"
    entry_point = "githubWebhook"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_source.name
        object = google_storage_bucket_object.github_webhook.name
      }
    }
  }

  service_config {
    max_instance_count = 10
    min_instance_count = 0
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
    }
    secret_environment_variables {
      key        = "GITHUB_WEBHOOK_SECRET"
      secret     = var.github_app_webhook_secret_name
      version    = "latest"
      project_id = var.project_number
    }
    ingress_settings               = "ALLOW_ALL"
    all_traffic_on_latest_revision = true
  }

  depends_on = [
    google_storage_bucket_object.github_webhook,
    google_secret_manager_secret_iam_member.github_app_webhook_secret_cloudrun,
  ]
}

# Allow unauthenticated (GitHub must reach the webhook).
resource "google_cloud_run_v2_service_iam_member" "github_webhook_public" {
  location = google_cloudfunctions2_function.github_webhook.location
  name     = google_cloudfunctions2_function.github_webhook.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
