# Secret Manager secrets and their first/current version from Terraform variables.
# Set values in secrets.tfvars (gitignored) or TF_VAR_*; run terraform apply to create/update.
# GDPR: replication is EU-only (europe-west1) so no data leaves the EU.

resource "google_secret_manager_secret" "anthropic_api_key" {
  project   = var.project_id
  secret_id = "refactor-agent-anthropic-api-key"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "chainlit_auth_secret" {
  project   = var.project_id
  secret_id = "refactor-agent-chainlit-auth-secret"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.secretmanager]
}

# Secret versions from variables (only when set). Change keys in secrets.tfvars and apply.
resource "google_secret_manager_secret_version" "anthropic_api_key" {
  count       = length(var.anthropic_api_key) > 0 ? 1 : 0
  secret      = google_secret_manager_secret.anthropic_api_key.id
  secret_data = var.anthropic_api_key
}

resource "google_secret_manager_secret_version" "chainlit_auth_secret" {
  count       = length(var.chainlit_auth_secret) > 0 ? 1 : 0
  secret      = google_secret_manager_secret.chainlit_auth_secret.id
  secret_data = var.chainlit_auth_secret
}

# Optional: uncomment when using Langfuse in cloud (same EU-only replication).
# resource "google_secret_manager_secret" "langfuse_public_key" {
#   project   = var.project_id
#   secret_id = "refactor-agent-langfuse-public-key"
#   replication { user_managed { replicas { location = var.region } } }
#   depends_on = [google_project_service.secretmanager]
# }
# resource "google_secret_manager_secret" "langfuse_secret_key" {
#   project   = var.project_id
#   secret_id = "refactor-agent-langfuse-secret-key"
#   replication { user_managed { replicas { location = var.region } } }
#   depends_on = [google_project_service.secretmanager]
# }
