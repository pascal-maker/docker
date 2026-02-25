# Firebase Hosting site for the marketing SPA.
# Requires: add GCP project to Firebase Console first (manual step).
# Deploy built files via: firebase deploy --only hosting (CI or manual).
# Note: Firebase Hosting API and project must be set up in Firebase Console before apply.
resource "google_firebase_hosting_site" "default" {
  count    = 0 # Disabled until Firebase project is added; set to 1 when ready
  provider = google-beta
  project  = var.project_id
  site_id  = var.project_id
}
