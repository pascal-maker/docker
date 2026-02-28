# Email notify Cloud Function: Firestore onCreate users/{userId} -> Resend admin email.
# TypeScript (nodejs24). Run `make functions-build` before terraform apply.

data "archive_file" "email_notify" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/email_notify/.deploy"
  output_path = "${path.module}/.build/email_notify.zip"
}

resource "google_storage_bucket_object" "email_notify" {
  name   = "email_notify-${data.archive_file.email_notify.output_md5}.zip"
  bucket = google_storage_bucket.functions_source.name
  source = data.archive_file.email_notify.output_path
}

resource "google_cloudfunctions2_function" "email_notify" {
  name     = "email-notify-pending-user"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "nodejs24"
    entry_point = "onUserCreated"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_source.name
        object = google_storage_bucket_object.email_notify.name
      }
    }
  }

  service_config {
    max_instance_count = 10
    min_instance_count = 0
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      ADMIN_EMAIL = var.admin_email
      FROM_EMAIL  = "Refactor Agent <noreply@refactorum.com>"
    }
    # Terraform docs: secret = name only (not full resource path); project_id = project number preferred.
    secret_environment_variables {
      key        = "RESEND_API_KEY"
      secret     = "refactor-agent-resend-api-key"
      version    = "latest"
      project_id = var.project_number
    }
    ingress_settings               = "ALLOW_INTERNAL_ONLY"
    all_traffic_on_latest_revision = true
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.firestore.document.v1.created"
    event_filters {
      attribute = "database"
      value     = "(default)"
    }
    event_filters {
      attribute = "document"
      value     = "users/{userId}"
    }
  }

  depends_on = [
    google_storage_bucket_object.email_notify,
    google_secret_manager_secret_iam_member.resend_api_key_cloudrun,
    google_project_iam_member.eventarc_event_receiver,
  ]
}
