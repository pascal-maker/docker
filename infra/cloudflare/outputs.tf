output "resend_spf_record" {
  description = "Resend SPF TXT record (created)."
  value       = cloudflare_dns_record.resend_spf.name
}
