# SSL/TLS mode: Full (strict) so Cloudflare connects to Firebase Hosting over HTTPS.
# Required when proxying Firebase; Flexible mode can cause redirect loops or 502s.
# Uses cloudflare_zone_setting (v5+) to avoid read-only settings in zone_settings_override.
resource "cloudflare_zone_setting" "ssl" {
  zone_id    = var.zone_id
  setting_id = "ssl"
  value      = "strict"
}
