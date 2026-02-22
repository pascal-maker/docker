# Service account for GitHub Actions: used to run gcloud builds submit and push images.
# Create a key for this SA and add the JSON to repo secret GCP_SA_KEY (do not commit the key).

resource "google_service_account" "github_actions" {
  project      = var.project_id
  account_id   = "refactor-agent-github-actions"
  display_name = "GitHub Actions (build and push images)"
}

# Allow the SA to submit Cloud Build jobs (gcloud builds submit). Cloud Build's default SA does the actual push to Artifact Registry.
resource "google_project_iam_member" "github_actions_cloudbuild" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

output "github_actions_sa_email" {
  description = "Service account email for GitHub Actions; use with gcloud iam service-accounts keys create to create a key, then add the JSON to repo secret GCP_SA_KEY."
  value       = google_service_account.github_actions.email
}
