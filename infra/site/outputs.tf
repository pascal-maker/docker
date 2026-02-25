output "auth_callback_url" {
  description = "GitHub OAuth callback URL. Set this in GitHub OAuth App settings."
  value       = "https://${var.region}-${var.project_id}.cloudfunctions.net/auth-github-callback"
}

output "firebase_hosting_site_id" {
  description = "Firebase Hosting site ID (empty until firebase_hosting.tf count=1)."
  value       = try(google_firebase_hosting_site.default[0].site_id, "")
}
