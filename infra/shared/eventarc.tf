# Eventarc Service Agent: required for Firestore triggers (e.g. email_notify Cloud Function).
# The service agent is created when Eventarc is first used; grant the role so it can manage triggers.
# See: https://cloud.google.com/eventarc/advanced/docs/troubleshoot
resource "google_project_iam_member" "eventarc_service_agent" {
  project = var.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-eventarc.iam.gserviceaccount.com"
}
