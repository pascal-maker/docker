# Auth register device Cloud Function: POST with Bearer token -> Firestore user.
# Used by VS Code extension when device flow is used instead of browser redirect.

data "archive_file" "auth_register_device" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/auth_register_device"
  output_path = "${path.module}/.build/auth_register_device.zip"
}

resource "google_storage_bucket_object" "auth_register_device" {
  name   = "auth_register_device-${data.archive_file.auth_register_device.output_md5}.zip"
  bucket = google_storage_bucket.functions_source.name
  source = data.archive_file.auth_register_device.output_path
}

resource "google_cloudfunctions2_function" "auth_register_device" {
  name     = "auth-register-device"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python312"
    entry_point = "auth_register_device"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_source.name
        object = google_storage_bucket_object.auth_register_device.name
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
      GITHUB_APP_ID        = var.github_app_id
    }
    ingress_settings               = "ALLOW_ALL"
    all_traffic_on_latest_revision = true
  }

  depends_on = [google_storage_bucket_object.auth_register_device]
}

# Allow unauthenticated (extension calls with Bearer token).
resource "google_cloud_run_v2_service_iam_member" "auth_register_device_public" {
  location = google_cloudfunctions2_function.auth_register_device.location
  name     = google_cloudfunctions2_function.auth_register_device.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
