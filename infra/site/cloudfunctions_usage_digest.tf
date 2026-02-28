# Usage digest Cloud Function: HTTP trigger, runs daily via Cloud Scheduler.
# Queries Firestore + Cloud Monitoring, sends digest email via Resend.
# TypeScript (nodejs24). Run `make functions-build` before terraform apply.

data "archive_file" "usage_digest" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/usage_digest/.deploy"
  output_path = "${path.module}/.build/usage_digest.zip"
}

resource "google_storage_bucket_object" "usage_digest" {
  name   = "usage_digest-${data.archive_file.usage_digest.output_md5}.zip"
  bucket = google_storage_bucket.functions_source.name
  source = data.archive_file.usage_digest.output_path
}

resource "google_cloudfunctions2_function" "usage_digest" {
  name     = "usage-digest"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "nodejs24"
    entry_point = "usageDigest"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_source.name
        object = google_storage_bucket_object.usage_digest.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    min_instance_count = 0
    available_memory   = "256Mi"
    timeout_seconds    = 120
    environment_variables = {
      ADMIN_EMAIL          = var.admin_email
      FROM_EMAIL           = "Refactor Agent <noreply@refactorum.com>"
      GOOGLE_CLOUD_PROJECT = var.project_id
    }
    secret_environment_variables {
      key        = "RESEND_API_KEY"
      secret     = "refactor-agent-resend-api-key"
      version    = "latest"
      project_id = var.project_number
    }
    ingress_settings               = "ALLOW_INTERNAL_AND_GCLB"
    all_traffic_on_latest_revision = true
  }

  depends_on = [
    google_storage_bucket_object.usage_digest,
    google_secret_manager_secret_iam_member.resend_api_key_cloudrun,
  ]
}

# No allUsers: only Cloud Scheduler (via its SA) can invoke. See cloudscheduler_usage_digest.tf.
