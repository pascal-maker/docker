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
