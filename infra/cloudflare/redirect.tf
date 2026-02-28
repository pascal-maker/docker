# Redirect www.refactorum.com to refactorum.com (301) for SEO and canonical URL.
# Requires: Cloudflare proxy enabled on Firebase DNS records (proxied = true).
# v5: rules is an attribute (list), not a block.
resource "cloudflare_ruleset" "www_to_apex" {
  zone_id     = var.zone_id
  name        = "www-to-apex-redirect"
  description = "Redirect www.refactorum.com to refactorum.com (301)"
  kind        = "zone"
  phase       = "http_request_dynamic_redirect"

  rules = [{
    expression  = "http.host eq \"www.${var.zone_name}\""
    description = "Redirect www to apex"
    action      = "redirect"
    action_parameters = {
      from_value = {
        target_url = {
          expression = "concat(\"https://\", \"${var.zone_name}\", http.request.uri.path)"
        }
        status_code           = 301
        preserve_query_string = true
      }
    }
  }]
}
