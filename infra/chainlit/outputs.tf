output "chainlit_url" {
  description = "URL of the Chainlit Cloud Run service (empty when chainlit_image is not set)."
  value       = try(google_cloud_run_v2_service.chainlit[0].uri, "")
}
