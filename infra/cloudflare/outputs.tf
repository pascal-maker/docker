output "resend_spf_record" {
  description = "Resend SPF TXT record (created)."
  value       = cloudflare_record.resend_spf.hostname
}
