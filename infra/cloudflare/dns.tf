# DNS records for refactorum.com.
# Add domain in Resend and Firebase first to get DKIM and hosting targets.

# Resend SPF - required for sending from noreply@refactorum.com.
resource "cloudflare_dns_record" "resend_spf" {
  zone_id = var.zone_id
  name    = "@"
  type    = "TXT"
  content = "v=spf1 include:resend.com ~all"
  ttl     = 3600
}

# Resend DKIM - from Resend Dashboard after adding domain. Resend may show CNAME or TXT.
resource "cloudflare_dns_record" "resend_dkim" {
  count   = var.resend_dkim_name != "" && var.resend_dkim_target != "" ? 1 : 0
  zone_id = var.zone_id
  name    = var.resend_dkim_name
  type    = var.resend_dkim_type
  content = var.resend_dkim_target
  ttl     = 3600
}

# Manual fallback when firebase_custom_domain is not set.
resource "cloudflare_dns_record" "firebase_hosting_manual" {
  count   = var.firebase_hosting_target != "" ? 1 : 0
  zone_id = var.zone_id
  name    = var.firebase_hosting_name
  type    = var.firebase_hosting_type
  content = var.firebase_hosting_target
  ttl     = 1
  proxied = true
}

# Firebase Hosting - explicit records from Firebase Console "Needs setup" dialog.
# These are stable for the refactor-agent Firebase project.
resource "cloudflare_dns_record" "firebase_apex_a" {
  zone_id = var.zone_id
  name    = "@"
  type    = "A"
  content = "199.36.158.100"
  ttl     = 1
  proxied = true
}

resource "cloudflare_dns_record" "firebase_apex_txt" {
  zone_id = var.zone_id
  name    = "@"
  type    = "TXT"
  content = "hosting-site=refactor-agent"
  ttl     = 3600
}

resource "cloudflare_dns_record" "firebase_www_cname" {
  zone_id = var.zone_id
  name    = "www"
  type    = "CNAME"
  content = "refactor-agent.web.app"
  ttl     = 1
  proxied = true
}

resource "cloudflare_dns_record" "firebase_www_txt" {
  zone_id = var.zone_id
  name    = "www"
  type    = "TXT"
  content = "hosting-site=refactor-agent"
  ttl     = 3600
}
