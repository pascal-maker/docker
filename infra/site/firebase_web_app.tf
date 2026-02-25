# Firebase Web App for the marketing site.
# Creates the app and exposes Measurement ID for consent-gated analytics.
# Requires: GCP project added to Firebase Console first (one-time manual step).
resource "google_firebase_web_app" "site" {
  provider     = google-beta
  project      = var.project_id
  display_name = "Refactorum"
}

data "google_firebase_web_app_config" "site" {
  provider   = google-beta
  web_app_id = google_firebase_web_app.site.app_id
}
