#!/usr/bin/env bash
# Import existing GCP resources into Terraform state after a state wipe.
# Run from infra/ with backend already initialized.
# Usage: ./scripts/import-existing.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-refactor-agent}"
VAR_FILES="-var-file=dev.tfvars -var-file=secrets.tfvars"

echo "Importing existing resources into Terraform state (project=${PROJECT_ID})..."

# Shared module - Artifact Registry repository
terraform import $VAR_FILES 'module.shared.google_artifact_registry_repository.refactor_agent' "projects/${PROJECT_ID}/locations/europe-west1/repositories/refactor-agent"

# Shared module - Cloud Build GCS bucket (created by gcloud or previous apply)
terraform import $VAR_FILES 'module.shared.google_storage_bucket.cloudbuild' "${PROJECT_ID}_cloudbuild"

# Shared module - Firestore default database
terraform import $VAR_FILES 'module.shared.google_firestore_database.default' "projects/${PROJECT_ID}/databases/(default)"

# Shared module - GitHub Actions service account
terraform import $VAR_FILES 'module.shared.google_service_account.github_actions' "projects/${PROJECT_ID}/serviceAccounts/refactor-agent-github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Shared module - Secret Manager secrets
terraform import $VAR_FILES 'module.shared.google_secret_manager_secret.anthropic_api_key' "projects/${PROJECT_ID}/secrets/refactor-agent-anthropic-api-key"
terraform import $VAR_FILES 'module.shared.google_secret_manager_secret.chainlit_auth_secret' "projects/${PROJECT_ID}/secrets/refactor-agent-chainlit-auth-secret"

echo "Imports done. Run: terraform plan -var-file=dev.tfvars -var-file=secrets.tfvars"
echo "Then import any remaining resources that plan says it will create but already exist, and run apply."
