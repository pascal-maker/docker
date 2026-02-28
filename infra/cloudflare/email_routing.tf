# Cloudflare Email Routing: receive-only. Forwards noreply@ and admin@ (refactorum.com) to real inbox.

# Destination address (must verify once via link Cloudflare sends).
resource "cloudflare_email_routing_address" "destination" {
  account_id = var.account_id
  email      = var.email_destination
}

# Rule: noreply@refactorum.com -> destination.
# v5: matchers and actions are list attributes.
resource "cloudflare_email_routing_rule" "noreply" {
  zone_id = var.zone_id
  name    = "noreply to destination"
  enabled = true

  matchers = [{
    type  = "literal"
    field = "to"
    value = "noreply@refactorum.com"
  }]

  actions = [{
    type  = "forward"
    value = [var.email_destination]
  }]
}

# Rule: admin@refactorum.com -> destination.
resource "cloudflare_email_routing_rule" "admin" {
  zone_id = var.zone_id
  name    = "admin to destination"
  enabled = true

  matchers = [{
    type  = "literal"
    field = "to"
    value = "admin@refactorum.com"
  }]

  actions = [{
    type  = "forward"
    value = [var.email_destination]
  }]
}
