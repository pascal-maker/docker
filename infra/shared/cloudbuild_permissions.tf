# Permissions so Cloud Build can read the uploaded source and push images.
# The build runs as the default Compute Engine SA (or Cloud Build SA); both need access
# to the Cloud Build GCS bucket and to Artifact Registry. Keeps everything in IaC for a small team.

# Bucket used by gcloud builds submit for source uploads. Same region as rest of infra (europe-west1 = Belgium, Ghent area).
# If this bucket already exists (e.g. from a prior gcloud builds submit), import it:
#   terraform import -var-file=dev.tfvars module.shared.google_storage_bucket.cloudbuild PROJECT_ID_cloudbuild
resource "google_storage_bucket" "cloudbuild" {
  project                     = var.project_id
  name                        = "${var.project_id}_cloudbuild"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  depends_on                  = [google_project_service.storage]

  # If the bucket was created by GCP/Cloud Build in another region (e.g. US), importing it would
  # otherwise force replacement (location is immutable). Keep existing location.
  lifecycle {
    ignore_changes = [location]
  }
}

# Default Compute Engine SA (often used by Cloud Build to run the build).
locals {
  compute_sa_email    = "${data.google_project.project.number}-compute@developer.gserviceaccount.com"
  cloudbuild_sa_email = "${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# So the build can read the uploaded tarball.
resource "google_storage_bucket_iam_member" "cloudbuild_bucket_compute_sa" {
  bucket = google_storage_bucket.cloudbuild.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${local.compute_sa_email}"
}

resource "google_storage_bucket_iam_member" "cloudbuild_bucket_cloudbuild_sa" {
  bucket = google_storage_bucket.cloudbuild.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${local.cloudbuild_sa_email}"
}

# GitHub Actions SA must be able to upload source to this bucket when running gcloud builds submit.
resource "google_storage_bucket_iam_member" "cloudbuild_bucket_github_actions" {
  bucket = google_storage_bucket.cloudbuild.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_actions.email}"
}

# Allow GitHub Actions SA to read/write Terraform state when running deploy in CI (optional; set terraform_state_bucket in tfvars).
# Uses storage.admin (not objectAdmin) so Terraform can get/set IAM policy on the bucket (storage.buckets.getIamPolicy).
resource "google_storage_bucket_iam_member" "terraform_state_github_actions" {
  count  = length(var.terraform_state_bucket) > 0 ? 1 : 0
  bucket = var.terraform_state_bucket
  role   = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.github_actions.email}"
}

# So the build can push the image to Artifact Registry.
resource "google_artifact_registry_repository_iam_member" "cloudbuild_compute_sa" {
  project    = var.project_id
  location   = google_artifact_registry_repository.refactor_agent.location
  repository = google_artifact_registry_repository.refactor_agent.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${local.compute_sa_email}"
}

resource "google_artifact_registry_repository_iam_member" "cloudbuild_cloudbuild_sa" {
  project    = var.project_id
  location   = google_artifact_registry_repository.refactor_agent.location
  repository = google_artifact_registry_repository.refactor_agent.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${local.cloudbuild_sa_email}"
}

# Cloud Functions Gen2 build: Cloud Build SA needs Cloud Functions Developer and actAs on compute SA.
resource "google_project_iam_member" "cloudbuild_cloudfunctions_developer" {
  project = var.project_id
  role    = "roles/cloudfunctions.developer"
  member  = "serviceAccount:${local.cloudbuild_sa_email}"
}

resource "google_service_account_iam_member" "cloudbuild_act_as_compute" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${local.compute_sa_email}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.cloudbuild_sa_email}"
}

# Cloud Build default change (July 2024): new projects use Compute SA for builds with insufficient
# permissions. Grant Cloud Build Account role so it can build Cloud Functions.
# See: https://cloud.google.com/functions/docs/securing/build-custom-sa
resource "google_project_iam_member" "compute_sa_cloudbuild_builder" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${local.compute_sa_email}"
}
