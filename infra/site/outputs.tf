output "auth_callback_url" {
  description = "GitHub OAuth callback URL. Set this in GitHub OAuth App settings."
  value       = "https://${var.region}-${var.project_id}.cloudfunctions.net/auth-github-callback"
}

output "github_webhook_url" {
  description = "GitHub App webhook URL. Set in GitHub App → Webhook settings."
  value       = "https://${var.region}-${var.project_id}.cloudfunctions.net/github-webhook"
}

output "auth_register_device_url" {
  description = "Auth register device URL. Used by extension for device flow fallback."
  value       = "https://${var.region}-${var.project_id}.cloudfunctions.net/auth-register-device"
}

output "firebase_hosting_site_id" {
  description = "Firebase Hosting site ID (empty until firebase_hosting.tf count=1)."
  value       = try(google_firebase_hosting_site.default[0].site_id, "")
}

output "firebase_measurement_id" {
  description = "Firebase Analytics Measurement ID (G-...) for consent-gated analytics."
  value       = try(data.google_firebase_web_app_config.site.measurement_id, "")
}
