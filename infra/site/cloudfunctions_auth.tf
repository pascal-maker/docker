# Auth callback Cloud Function: GitHub OAuth -> Firestore user with status=pending.

data "archive_file" "auth_callback" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/auth_callback"
  output_path = "${path.module}/.build/auth_callback.zip"
}

resource "google_storage_bucket_object" "auth_callback" {
  name   = "auth_callback-${data.archive_file.auth_callback.output_md5}.zip"
  bucket = google_storage_bucket.functions_source.name
  source = data.archive_file.auth_callback.output_path
}

resource "google_cloudfunctions2_function" "auth_callback" {
  name     = "auth-github-callback"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python312"
    entry_point = "auth_callback"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_source.name
        object = google_storage_bucket_object.auth_callback.name
      }
    }
  }

  service_config {
    max_instance_count = 10
    min_instance_count = 0
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      SITE_URL               = var.site_url
      GITHUB_OAUTH_CLIENT_ID = var.github_oauth_client_id
      GITHUB_OAUTH_REDIRECT_URI = "https://${var.region}-${var.project_id}.cloudfunctions.net/auth-github-callback"
      GOOGLE_CLOUD_PROJECT   = var.project_id
    }
    # Terraform docs: secret = name only (not full resource path); project_id = project number preferred.
    secret_environment_variables {
      key        = "GITHUB_OAUTH_CLIENT_SECRET"
      secret     = "refactor-agent-github-oauth-client-secret"
      version    = "latest"
      project_id = var.project_number
    }
    ingress_settings               = "ALLOW_ALL"
    all_traffic_on_latest_revision  = true
  }

  depends_on = [
    google_storage_bucket_object.auth_callback,
    google_secret_manager_secret_iam_member.github_oauth_cloudrun,
  ]
}

# Allow unauthenticated (OAuth callback must be publicly reachable).
resource "google_cloud_run_v2_service_iam_member" "auth_callback_public" {
  location = google_cloudfunctions2_function.auth_callback.location
  name     = google_cloudfunctions2_function.auth_callback.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
