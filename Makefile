.DEFAULT_GOAL := help

RUN := uv run
TS_BRIDGE := src/refactor_agent/engine/typescript/bridge
TS_PACKAGES := dashboard-ui $(TS_BRIDGE) vscode-extension
# Workspace package names (for pnpm --filter)
TS_FILTERS := dashboard-ui site @refactor-agent/design-system ts-morph-bridge refactor-agent

INFRA_VAR_FILE ?= dev.tfvars
GCP_PROJECT_ID ?= refactor-agent
A2A_IMAGE_TAG  ?= latest

.PHONY: help format format-check lint fix typecheck test check ci clean ui dashboard dashboard-ui reset-playground ts-install ts-engine-install ts-engine-check ts-format-check ts-lint ts-typecheck ts-knip dead-code deprecation-check pre-commit-install infra-bootstrap infra-validate infra-fmt image-push infra-apply infra-gha-key infra-a2a-url sync-sentry-dsns probe-a2a check-a2a-security

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

format: ## Auto-format code
	$(RUN) ruff format src tests scripts

format-check: ## Check formatting (no changes)
	$(RUN) ruff format --check --diff src tests scripts

lint: ## Run ruff linter
	$(RUN) ruff check src tests scripts

fix: ## Auto-fix lint violations
	$(RUN) ruff check --fix src tests scripts

typecheck: ## Run mypy strict type checking (src only; scripts are one-off tools)
	$(RUN) mypy src

test: ## Run pytest
	$(RUN) pytest

check: ## Run all checks (format-check + lint + typecheck + test)
	@echo "=== Format Check ==="
	$(MAKE) format-check
	@echo "\n=== Lint ==="
	$(MAKE) lint
	@echo "\n=== Type Check ==="
	$(MAKE) typecheck
	@echo "\n=== Tests ==="
	$(MAKE) test
	@echo "\n=== All checks passed ==="

ci: ## Alias for check (CI usage)
	$(MAKE) check

ui: ## Launch Chainlit dev UI (reads playground/ directly)
	CHAINLIT_APP_ROOT=src $(RUN) chainlit run src/refactor_agent/ui/app.py -w

dashboard: ## Run refactor-issues dashboard backend (API; serves SPA if dashboard-ui/dist exists)
	$(RUN) python -m refactor_agent.dashboard

dashboard-ui: ## Run dashboard React UI dev server (proxy to backend on :8000)
	cd dashboard-ui && pnpm dev

dashboard-seed: ## Seed local dashboard DB with example check runs (for preview)
	$(RUN) python scripts/seed/seed_dashboard.py

reset-playground: ## Reset playground/nestjs-layered-architecture to origin/main (clean state)
	./scripts/dev/reset-playground.sh

ts-engine-install: ## Install TS workspace deps (bridge + dashboard-ui + vscode-extension). Use from repo root.
	pnpm install

ts-install: ## Install all TS workspace dependencies (single lockfile at root)
	pnpm install

ts-engine-check: ## Typecheck the ts-morph bridge
	cd $(TS_BRIDGE) && pnpm exec tsc --noEmit

ts-format-check: ## TypeScript format check (all TS packages except playground)
	@for pkg in $(TS_FILTERS); do echo "=== $$pkg ==="; pnpm --filter $$pkg run format-check; done

ts-lint: ## TypeScript lint (all TS packages except playground)
	@for pkg in $(TS_FILTERS); do echo "=== $$pkg ==="; pnpm --filter $$pkg run lint; done

ts-typecheck: ## TypeScript typecheck (all TS packages except playground)
	@for pkg in $(TS_FILTERS); do echo "=== $$pkg ==="; pnpm --filter $$pkg run typecheck; done

ts-knip: ## Knip: find dead code, unused exports, unused deps (TS)
	pnpm run knip

dead-code: ## Vulture: find dead code in Python (run after uv sync)
	$(RUN) vulture src tests scripts

deprecation-check: ## Flake8 deprecation plugin: flag deprecated API usage (Python)
	$(RUN) flake8 --select=D src tests scripts

pre-commit-install: ## Install pre-commit hooks (run once after clone)
	$(RUN) pre-commit install

clean: ## Remove caches and build artifacts
	rm -rf .ruff_cache .pytest_cache .mypy_cache dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# --- Infra (Terraform / GCP): run in order 1 → 2 → 3 → 4 ---
infra-validate: ## Terraform format check + init + validate (no backend; CI and local)
	cd infra && terraform fmt -check -recursive -diff
	cd infra && terraform init -backend=false
	cd infra && terraform validate

infra-fmt: ## Format Terraform files
	cd infra && terraform fmt -recursive

infra-bootstrap: ## 1) Cloud Build + Storage API, build bucket and IAM (set INFRA_VAR_FILE if not dev.tfvars)
	cd infra && terraform apply \
		-target=google_project_service.cloudbuild \
		-target=google_project_service.storage \
		-target=google_storage_bucket.cloudbuild \
		-target=google_storage_bucket_iam_member.cloudbuild_bucket_compute_sa \
		-target=google_storage_bucket_iam_member.cloudbuild_bucket_cloudbuild_sa \
		-target=google_artifact_registry_repository_iam_member.cloudbuild_compute_sa \
		-target=google_artifact_registry_repository_iam_member.cloudbuild_cloudbuild_sa \
		-var-file=$(INFRA_VAR_FILE)

image-push: ## 2) Build and push A2A image to Artifact Registry (uses Docker layer cache via cloudbuild.yaml)
	gcloud builds submit --config=cloudbuild.yaml \
		--substitutions=_IMAGE_URL=europe-west1-docker.pkg.dev/$(GCP_PROJECT_ID)/refactor-agent/a2a-server:$(A2A_IMAGE_TAG) \
		. --project=$(GCP_PROJECT_ID)

infra-apply: ## 3) Full Terraform apply – APIs, secrets, SA, Cloud Run (requires infra/secrets.tfvars)
	@cd infra && \
	if [ -f firebase-sa.json ]; then \
		terraform apply -var-file=$(INFRA_VAR_FILE) -var-file=secrets.tfvars \
			-var="firebase_service_account_json=$$(cat firebase-sa.json | jq -c .)"; \
	else \
		terraform apply -var-file=$(INFRA_VAR_FILE) -var-file=secrets.tfvars; \
	fi

infra-gha-key: ## 4) Create GitHub Actions SA key → gh-actions-key.json (add as GCP_SA_KEY in repo secrets, then rm file)
	@SA_EMAIL=$$(terraform -chdir=infra output -raw github_actions_sa_email 2>/dev/null) && \
		test -n "$$SA_EMAIL" || (echo "Run make infra-apply first."; exit 1) && \
		gcloud iam service-accounts keys create gh-actions-key.json \
			--iam-account=$$SA_EMAIL --project=$(GCP_PROJECT_ID) && \
		echo "Add gh-actions-key.json to GitHub repo secret GCP_SA_KEY, then: rm gh-actions-key.json"

infra-a2a-url: ## Write A2A Cloud Run URL to .refactor-agent-a2a-url (extension reads it; no manual config)
	@url=$$(terraform -chdir=infra output -raw a2a_url 2>/dev/null) && \
		echo -n "$$url" > .refactor-agent-a2a-url && \
		echo "$$url" && \
		echo "(written to .refactor-agent-a2a-url; extension will use it in this workspace)"

sync-sentry-dsns: ## Sync Sentry DSNs from Terraform into .env files (run after terraform apply)
	./scripts/infra/sync_sentry_dsns.sh

# A2A staging/prod probe and security check (override A2A_URL or use .refactor-agent-a2a-url)
A2A_URL ?= $(shell test -f .refactor-agent-a2a-url && cat .refactor-agent-a2a-url || echo "http://localhost:9999")
probe-a2a: ## Probe A2A endpoint: what is reachable with/without auth
	$(RUN) python scripts/a2a/probe_a2a.py "$(A2A_URL)"

check-a2a-security: ## Programmatic A2A security check; REQUIRE_AUTH_FOR_SEND=1 to fail if POST without auth succeeds
	$(RUN) python scripts/a2a/check_a2a_security.py --base-url "$(A2A_URL)" $(if $(REQUIRE_AUTH_FOR_SEND),--require-auth-for-send,)
