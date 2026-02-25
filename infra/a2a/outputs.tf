output "a2a_url" {
  description = "URL of the deployed A2A Cloud Run service."
  value       = google_cloud_run_v2_service.a2a.uri
}
