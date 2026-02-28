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

# Resend DKIM - from Resend Dashboard after adding domain. Resend may show CNAME or TXT.
resource "cloudflare_record" "resend_dkim" {
  count   = var.resend_dkim_name != "" && var.resend_dkim_target != "" ? 1 : 0
  zone_id = var.zone_id
  name    = var.resend_dkim_name
  type    = var.resend_dkim_type
  content = var.resend_dkim_target
  ttl     = 3600
}

# Firebase Hosting - Terraform-managed (from Firebase custom domain) or manual (firebase_hosting_* vars).
# Exclude records we already create (resend_spf, resend_dkim) to avoid "already exists" conflicts.
locals {
  firebase_use_terraform = length(var.firebase_custom_domain_dns_updates) > 0
  firebase_dns_records_raw = local.firebase_use_terraform ? flatten([
    for update in var.firebase_custom_domain_dns_updates : [
      for desired in try(update.desired, []) : [
        for rec in try(desired.records, []) : {
          name    = desired.domain_name == var.zone_name ? "@" : replace(desired.domain_name, "${var.zone_name}.", "")
          type    = rec.type
          content = rec.rdata
          key     = "${desired.domain_name}-${rec.type}-${rec.rdata}"
        }
      ]
    ]
  ]) : []
  # Skip SPF (already in resend_spf) and DKIM (already in resend_dkim).
  firebase_dns_records = [
    for r in local.firebase_dns_records_raw : r
    if !(r.name == "@" && r.type == "TXT" && r.content == "v=spf1 include:resend.com ~all")
    && !(var.resend_dkim_name != "" && r.name == var.resend_dkim_name && r.type == var.resend_dkim_type)
  ]
  firebase_dns_records_map = { for r in local.firebase_dns_records : r.key => r }
}

resource "cloudflare_record" "firebase_hosting_terraform" {
  for_each = local.firebase_dns_records_map
  zone_id  = var.zone_id
  name     = each.value.name
  type     = each.value.type
  content  = each.value.content
  ttl      = 3600
  proxied  = false
}

# Manual fallback when firebase_custom_domain is not set.
resource "cloudflare_record" "firebase_hosting_manual" {
  count   = !local.firebase_use_terraform && var.firebase_hosting_target != "" ? 1 : 0
  zone_id = var.zone_id
  name    = var.firebase_hosting_name
  type    = var.firebase_hosting_type
  content = var.firebase_hosting_target
  ttl     = 3600
  proxied = false
}
