# Bucket for Cloud Functions source archives.
resource "google_storage_bucket" "functions_source" {
  project                     = var.project_id
  name                        = "${var.project_id}-functions-source"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
}

# Cloud Functions Gen2 build reads source from this bucket. Grant Cloud Build and compute SAs access.
resource "google_storage_bucket_iam_member" "functions_source_cloudbuild_sa" {
  bucket = google_storage_bucket.functions_source.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.project_number}@cloudbuild.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "functions_source_compute_sa" {
  bucket = google_storage_bucket.functions_source.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}
