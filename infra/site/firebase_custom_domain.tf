# Firebase Hosting custom domains. Fully managed via Terraform.
# Registers each domain with Firebase and outputs required DNS records for Cloudflare.
# Requires: GCP project added to Firebase (manual one-time step).
# The default hosting site (site_id = project_id) must exist.

moved {
  from = google_firebase_hosting_custom_domain.site[0]
  to   = google_firebase_hosting_custom_domain.site["refactorum.com"]
}

resource "google_firebase_hosting_custom_domain" "site" {
  for_each              = toset(var.firebase_custom_domains)
  provider              = google-beta
  project               = var.project_id
  site_id               = var.project_id
  custom_domain         = each.value
  wait_dns_verification = false
}
