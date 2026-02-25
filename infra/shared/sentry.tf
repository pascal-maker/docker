# Sentry projects and keys (IaC). Requires sentry_organization and SENTRY_AUTH_TOKEN.
# Issue alerts: email to active org members (free tier; Slack requires paid plan).

locals {
  sentry_enabled = var.sentry_organization != ""
}

# Team for refactor-agent projects (Sentry requires projects to belong to a team).
resource "sentry_team" "refactor_agent" {
  count        = local.sentry_enabled ? 1 : 0
  organization = var.sentry_organization
  name         = "Refactor Agent"
  slug         = "refactor-agent"
}

# Backend project (Python: A2A, sync, dashboard, Chainlit, agent).
resource "sentry_project" "backend" {
  count         = local.sentry_enabled ? 1 : 0
  organization  = var.sentry_organization
  teams         = [sentry_team.refactor_agent[0].slug]
  name          = "Refactor Agent Backend"
  slug          = "refactor-agent-backend"
  platform      = "python"
  default_rules = false
}

# Frontend project (React: dashboard-ui, site).
resource "sentry_project" "frontend" {
  count         = local.sentry_enabled ? 1 : 0
  organization  = var.sentry_organization
  teams         = [sentry_team.refactor_agent[0].slug]
  name          = "Refactor Agent Frontend"
  slug          = "refactor-agent-frontend"
  platform      = "javascript-react"
  default_rules = false
}

# VS Code extension project.
resource "sentry_project" "vscode" {
  count         = local.sentry_enabled ? 1 : 0
  organization  = var.sentry_organization
  teams         = [sentry_team.refactor_agent[0].slug]
  name          = "Refactor Agent VS Code"
  slug          = "refactor-agent-vscode"
  platform      = "node"
  default_rules = false
}

# Client keys (DSN) per project.
resource "sentry_key" "backend" {
  count        = local.sentry_enabled ? 1 : 0
  organization = var.sentry_organization
  project      = sentry_project.backend[0].slug
  name         = "Default"
}

resource "sentry_key" "frontend" {
  count        = local.sentry_enabled ? 1 : 0
  organization = var.sentry_organization
  project      = sentry_project.frontend[0].slug
  name         = "Default"
}

resource "sentry_key" "vscode" {
  count        = local.sentry_enabled ? 1 : 0
  organization = var.sentry_organization
  project      = sentry_project.vscode[0].slug
  name         = "Default"
}

# Issue alerts: email active org members when a new issue is first seen (free tier).
resource "sentry_issue_alert" "backend_email" {
  count        = local.sentry_enabled ? 1 : 0
  organization = var.sentry_organization
  project      = sentry_project.backend[0].id
  name         = "Email on new issue"

  action_match = "any"
  filter_match = "any"
  frequency    = 30

  conditions_v2 = [
    { first_seen_event = {} }
  ]

  actions_v2 = [
    {
      notify_email = {
        target_type      = "IssueOwners"
        fallthrough_type = "ActiveMembers"
      }
    }
  ]
}

resource "sentry_issue_alert" "frontend_email" {
  count        = local.sentry_enabled ? 1 : 0
  organization = var.sentry_organization
  project      = sentry_project.frontend[0].id
  name         = "Email on new issue"

  action_match = "any"
  filter_match = "any"
  frequency    = 30

  conditions_v2 = [
    { first_seen_event = {} }
  ]

  actions_v2 = [
    {
      notify_email = {
        target_type      = "IssueOwners"
        fallthrough_type = "ActiveMembers"
      }
    }
  ]
}

resource "sentry_issue_alert" "vscode_email" {
  count        = local.sentry_enabled ? 1 : 0
  organization = var.sentry_organization
  project      = sentry_project.vscode[0].id
  name         = "Email on new issue"

  action_match = "any"
  filter_match = "any"
  frequency    = 30

  conditions_v2 = [
    { first_seen_event = {} }
  ]

  actions_v2 = [
    {
      notify_email = {
        target_type      = "IssueOwners"
        fallthrough_type = "ActiveMembers"
      }
    }
  ]
}
