# GCP + Terraform dev infrastructure (free tier).
# EU-only (europe-west1, Belgium) for GDPR; nothing outside the EU.
# See infra/README.md for prerequisites and usage.

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    sentry = {
      source  = "jianyuan/sentry"
      version = "~> 0.14"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2"
    }
    github = {
      source  = "integrations/github"
      version = "~> 6"
    }
  }

  # GCS backend: state and locking in EU. Create bucket first (see infra/README.md).
  #   gsutil mb -l europe-west1 gs://YOUR_PROJECT-terraform-state
  #   gsutil versioning set on gs://YOUR_PROJECT-terraform-state
  # Then: terraform init -reconfigure -backend-config="bucket=YOUR_PROJECT-terraform-state"
  backend "gcs" {
    bucket = "REPLACE_OR_USE_BACKEND_CONFIG"
    prefix = "refactor-agent-infra"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

provider "sentry" {
  token    = var.sentry_auth_token
  base_url = var.sentry_base_url != "" ? var.sentry_base_url : "https://sentry.io/api/"
}

# Cloudflare provider requires a valid-format token even when module is disabled (count=0).
# Use placeholder when empty so plan/apply can run without Cloudflare; no API calls when count=0.
provider "cloudflare" {
  api_token = var.cloudflare_api_token != "" ? var.cloudflare_api_token : "0000000000000000000000000000000000000000"
}

provider "github" {
  token = var.github_token
}

# Cloudflare zone for refactorum.com (domain registered at Cloudflare).
data "cloudflare_zone" "refactorum" {
  count = var.cloudflare_api_token != "" ? 1 : 0
  name  = "refactorum.com"
}

# Shared: APIs, Firestore, secrets, GitHub Actions SA, Artifact Registry, Cloud Build permissions, Sentry.
module "shared" {
  source = "./shared"

  project_id                   = var.project_id
  region                       = var.region
  anthropic_api_key            = var.anthropic_api_key
  chainlit_auth_secret          = var.chainlit_auth_secret
  github_oauth_client_secret    = var.github_oauth_client_secret
  resend_api_key               = var.resend_api_key
  terraform_state_bucket       = var.terraform_state_bucket
  sentry_organization         = var.sentry_organization
}

# A2A: Cloud Run service for the refactor backend.
module "a2a" {
  source = "./a2a"

  project_id                   = var.project_id
  region                       = var.region
  a2a_image                    = var.a2a_image
  a2a_min_instance_count       = var.a2a_min_instance_count
  anthropic_api_key_secret_name = module.shared.anthropic_api_key_secret_name
  project_number               = module.shared.project_number
  sentry_dsn_backend           = module.shared.sentry_dsn_backend

  depends_on = [module.shared]
}

# Chainlit: Optional Cloud Run service for Dev UI.
module "chainlit" {
  source = "./chainlit"

  project_id                 = var.project_id
  region                     = var.region
  chainlit_image             = var.chainlit_image
  chainlit_invoker_member    = var.chainlit_invoker_member
  chainlit_auth_secret_name  = module.shared.chainlit_auth_secret_name
  a2a_url                    = module.a2a.a2a_url
  project_number             = module.shared.project_number
  sentry_dsn_backend         = module.shared.sentry_dsn_backend

  depends_on = [module.a2a]
}

# Site: Marketing site hosting, auth callback, email notify.
module "site" {
  source = "./site"

  project_id                         = var.project_id
  project_number                     = module.shared.project_number
  region                             = var.region
  site_url                           = var.site_url
  github_oauth_client_id             = var.github_oauth_client_id
  github_oauth_client_secret_name    = module.shared.github_oauth_client_secret_name
  resend_api_key_secret_name         = module.shared.resend_api_key_secret_name
  admin_email                        = var.site_admin_email
}

# Cloudflare: DNS and Email Routing for refactorum.com.
module "cloudflare" {
  source = "./cloudflare"

  count = var.cloudflare_api_token != "" ? 1 : 0

  zone_id                 = data.cloudflare_zone.refactorum[0].id
  account_id              = data.cloudflare_zone.refactorum[0].account_id
  email_destination       = var.cloudflare_email_destination
  resend_dkim_name          = var.resend_dkim_name
  resend_dkim_target        = var.resend_dkim_target
  firebase_hosting_target   = var.firebase_hosting_target
  firebase_hosting_type     = var.firebase_hosting_type
  firebase_hosting_name     = var.firebase_hosting_name
}
