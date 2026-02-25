#!/usr/bin/env bash
# Migrate Terraform state from flat structure to modules after infra restructure.
# Run from infra/ with backend already initialized.
# Usage: ./scripts/migrate-state-to-modules.sh

set -euo pipefail

echo "Migrating Terraform state to module structure..."

# Shared module
terraform state mv 'google_project_service.run' 'module.shared.google_project_service.run' 2>/dev/null || true
terraform state mv 'google_project_service.cloudbuild' 'module.shared.google_project_service.cloudbuild' 2>/dev/null || true
terraform state mv 'google_project_service.artifactregistry' 'module.shared.google_project_service.artifactregistry' 2>/dev/null || true
terraform state mv 'google_project_service.secretmanager' 'module.shared.google_project_service.secretmanager' 2>/dev/null || true
terraform state mv 'google_project_service.firestore' 'module.shared.google_project_service.firestore' 2>/dev/null || true
terraform state mv 'google_project_service.storage' 'module.shared.google_project_service.storage' 2>/dev/null || true
terraform state mv 'google_project_service.cloudresourcemanager' 'module.shared.google_project_service.cloudresourcemanager' 2>/dev/null || true
terraform state mv 'google_project_service.cloudfunctions' 'module.shared.google_project_service.cloudfunctions' 2>/dev/null || true
terraform state mv 'google_project_service.eventarc' 'module.shared.google_project_service.eventarc' 2>/dev/null || true
terraform state mv 'google_firestore_database.default' 'module.shared.google_firestore_database.default' 2>/dev/null || true
terraform state mv 'google_secret_manager_secret.anthropic_api_key' 'module.shared.google_secret_manager_secret.anthropic_api_key' 2>/dev/null || true
terraform state mv 'google_secret_manager_secret.chainlit_auth_secret' 'module.shared.google_secret_manager_secret.chainlit_auth_secret' 2>/dev/null || true
terraform state mv 'google_secret_manager_secret_version.anthropic_api_key[0]' 'module.shared.google_secret_manager_secret_version.anthropic_api_key[0]' 2>/dev/null || true
terraform state mv 'google_secret_manager_secret_version.chainlit_auth_secret[0]' 'module.shared.google_secret_manager_secret_version.chainlit_auth_secret[0]' 2>/dev/null || true
terraform state mv 'google_service_account.github_actions' 'module.shared.google_service_account.github_actions' 2>/dev/null || true
terraform state mv 'data.google_project.project' 'module.shared.data.google_project.project' 2>/dev/null || true
terraform state mv 'google_artifact_registry_repository.refactor_agent' 'module.shared.google_artifact_registry_repository.refactor_agent' 2>/dev/null || true
terraform state mv 'google_storage_bucket.cloudbuild' 'module.shared.google_storage_bucket.cloudbuild' 2>/dev/null || true
terraform state mv 'google_storage_bucket_iam_member.cloudbuild_bucket_compute_sa' 'module.shared.google_storage_bucket_iam_member.cloudbuild_bucket_compute_sa' 2>/dev/null || true
terraform state mv 'google_storage_bucket_iam_member.cloudbuild_bucket_cloudbuild_sa' 'module.shared.google_storage_bucket_iam_member.cloudbuild_bucket_cloudbuild_sa' 2>/dev/null || true
terraform state mv 'google_storage_bucket_iam_member.cloudbuild_bucket_github_actions' 'module.shared.google_storage_bucket_iam_member.cloudbuild_bucket_github_actions' 2>/dev/null || true
terraform state mv 'google_storage_bucket_iam_member.terraform_state_github_actions[0]' 'module.shared.google_storage_bucket_iam_member.terraform_state_github_actions[0]' 2>/dev/null || true
terraform state mv 'google_artifact_registry_repository_iam_member.cloudbuild_compute_sa' 'module.shared.google_artifact_registry_repository_iam_member.cloudbuild_compute_sa' 2>/dev/null || true
terraform state mv 'google_artifact_registry_repository_iam_member.cloudbuild_cloudbuild_sa' 'module.shared.google_artifact_registry_repository_iam_member.cloudbuild_cloudbuild_sa' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_cloudbuild' 'module.shared.google_project_iam_member.github_actions_cloudbuild' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_service_usage' 'module.shared.google_project_iam_member.github_actions_service_usage' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_run_admin' 'module.shared.google_project_iam_member.github_actions_run_admin' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_secretmanager_admin' 'module.shared.google_project_iam_member.github_actions_secretmanager_admin' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_iam_sa_admin' 'module.shared.google_project_iam_member.github_actions_iam_sa_admin' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_security_admin' 'module.shared.google_project_iam_member.github_actions_security_admin' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_artifactregistry_admin' 'module.shared.google_project_iam_member.github_actions_artifactregistry_admin' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_firestore_owner' 'module.shared.google_project_iam_member.github_actions_firestore_owner' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_serviceusage_admin' 'module.shared.google_project_iam_member.github_actions_serviceusage_admin' 2>/dev/null || true
terraform state mv 'google_project_iam_member.github_actions_storage_admin' 'module.shared.google_project_iam_member.github_actions_storage_admin' 2>/dev/null || true
terraform state mv 'google_service_account_iam_member.github_actions_act_as_compute' 'module.shared.google_service_account_iam_member.github_actions_act_as_compute' 2>/dev/null || true

# Sentry (optional - may not exist; uses count so resources have [0] index)
terraform state mv 'sentry_team.refactor_agent[0]' 'module.shared.sentry_team.refactor_agent[0]' 2>/dev/null || true
terraform state mv 'sentry_project.backend[0]' 'module.shared.sentry_project.backend[0]' 2>/dev/null || true
terraform state mv 'sentry_project.frontend[0]' 'module.shared.sentry_project.frontend[0]' 2>/dev/null || true
terraform state mv 'sentry_project.vscode[0]' 'module.shared.sentry_project.vscode[0]' 2>/dev/null || true
terraform state mv 'sentry_key.backend[0]' 'module.shared.sentry_key.backend[0]' 2>/dev/null || true
terraform state mv 'sentry_key.frontend[0]' 'module.shared.sentry_key.frontend[0]' 2>/dev/null || true
terraform state mv 'sentry_key.vscode[0]' 'module.shared.sentry_key.vscode[0]' 2>/dev/null || true
terraform state mv 'sentry_issue_alert.backend_email[0]' 'module.shared.sentry_issue_alert.backend_email[0]' 2>/dev/null || true
terraform state mv 'sentry_issue_alert.frontend_email[0]' 'module.shared.sentry_issue_alert.frontend_email[0]' 2>/dev/null || true
terraform state mv 'sentry_issue_alert.vscode_email[0]' 'module.shared.sentry_issue_alert.vscode_email[0]' 2>/dev/null || true

# A2A module
terraform state mv 'google_secret_manager_secret_iam_member.anthropic_key_cloudrun' 'module.a2a.google_secret_manager_secret_iam_member.anthropic_key_cloudrun' 2>/dev/null || true
terraform state mv 'google_project_iam_member.cloudrun_firestore' 'module.a2a.google_project_iam_member.cloudrun_firestore' 2>/dev/null || true
terraform state mv 'google_cloud_run_v2_service.a2a' 'module.a2a.google_cloud_run_v2_service.a2a' 2>/dev/null || true
terraform state mv 'google_cloud_run_v2_service_iam_member.a2a_public' 'module.a2a.google_cloud_run_v2_service_iam_member.a2a_public' 2>/dev/null || true

# Chainlit module (optional - may not exist; uses count so resources have [0] index)
terraform state mv 'google_secret_manager_secret_iam_member.chainlit_auth_cloudrun[0]' 'module.chainlit.google_secret_manager_secret_iam_member.chainlit_auth_cloudrun[0]' 2>/dev/null || true
terraform state mv 'google_cloud_run_v2_service.chainlit[0]' 'module.chainlit.google_cloud_run_v2_service.chainlit[0]' 2>/dev/null || true
terraform state mv 'google_cloud_run_v2_service_iam_member.chainlit_invoker[0]' 'module.chainlit.google_cloud_run_v2_service_iam_member.chainlit_invoker[0]' 2>/dev/null || true

echo "State migration done. Run: terraform plan -var-file=dev.tfvars -var-file=secrets.tfvars"
echo "If plan shows unexpected changes, some state moves may have failed (resources may not have existed)."
