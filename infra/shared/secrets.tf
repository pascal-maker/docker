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

# Site: GitHub OAuth client secret (deprecated; add value via gcloud secrets versions add).
resource "google_secret_manager_secret" "github_oauth_client_secret" {
  project   = var.project_id
  secret_id = "refactor-agent-github-oauth-client-secret"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.secretmanager]
}

# Site: GitHub App client secret (add value via secrets.tfvars or gcloud secrets versions add).
resource "google_secret_manager_secret" "github_app_client_secret" {
  project   = var.project_id
  secret_id = "refactor-agent-github-app-client-secret"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.secretmanager]
}

# GitHub App private key (for webhook verification and token refresh).
resource "google_secret_manager_secret" "github_app_private_key" {
  project   = var.project_id
  secret_id = "refactor-agent-github-app-private-key"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.secretmanager]
}

# GitHub App webhook secret (for webhook signature verification).
resource "google_secret_manager_secret" "github_app_webhook_secret" {
  project   = var.project_id
  secret_id = "refactor-agent-github-webhook-secret"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.secretmanager]
}

# Site: Resend API key (add value via secrets.tfvars or gcloud secrets versions add).
resource "google_secret_manager_secret" "resend_api_key" {
  project   = var.project_id
  secret_id = "refactor-agent-resend-api-key"

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

resource "google_secret_manager_secret_version" "github_oauth_client_secret" {
  count       = length(var.github_oauth_client_secret) > 0 ? 1 : 0
  secret      = google_secret_manager_secret.github_oauth_client_secret.id
  secret_data = var.github_oauth_client_secret
}

resource "google_secret_manager_secret_version" "github_app_client_secret" {
  count       = length(var.github_app_client_secret) > 0 ? 1 : 0
  secret      = google_secret_manager_secret.github_app_client_secret.id
  secret_data = var.github_app_client_secret
}

resource "google_secret_manager_secret_version" "github_app_private_key" {
  count       = length(var.github_app_private_key) > 0 ? 1 : 0
  secret      = google_secret_manager_secret.github_app_private_key.id
  secret_data = var.github_app_private_key
}

resource "google_secret_manager_secret_version" "github_app_webhook_secret" {
  count       = length(var.github_app_webhook_secret) > 0 ? 1 : 0
  secret      = google_secret_manager_secret.github_app_webhook_secret.id
  secret_data = var.github_app_webhook_secret
}

resource "google_secret_manager_secret_version" "resend_api_key" {
  count       = length(var.resend_api_key) > 0 ? 1 : 0
  secret      = google_secret_manager_secret.resend_api_key.id
  secret_data = var.resend_api_key
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
