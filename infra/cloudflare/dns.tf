# DNS records for refactorum.com.
# Add domain in Resend and Firebase first to get DKIM and hosting targets.

# Resend SPF - required for sending from noreply@refactorum.com.
resource "cloudflare_record" "resend_spf" {
  zone_id = var.zone_id
  name    = "@"
  type    = "TXT"
  content = "v=spf1 include:resend.com ~all"
  ttl     = 3600
}

# Resend DKIM - from Resend Dashboard after adding domain.
resource "cloudflare_record" "resend_dkim" {
  count   = var.resend_dkim_name != "" && var.resend_dkim_target != "" ? 1 : 0
  zone_id = var.zone_id
  name    = var.resend_dkim_name
  type    = "CNAME"
  content = var.resend_dkim_target
  ttl     = 3600
}

# Firebase Hosting - from Firebase Console after adding custom domain.
resource "cloudflare_record" "firebase_hosting" {
  count   = var.firebase_hosting_target != "" ? 1 : 0
  zone_id = var.zone_id
  name    = var.firebase_hosting_name
  type    = var.firebase_hosting_type
  content = var.firebase_hosting_target
  ttl     = 3600
  proxied = false
}
