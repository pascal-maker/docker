.DEFAULT_GOAL := help

RUN := uv run

.PHONY: help format format-check lint fix typecheck test check ci clean ui

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

format: ## Auto-format code
	$(RUN) ruff format src tests scripts playground

format-check: ## Check formatting (no changes)
	$(RUN) ruff format --check --diff src tests scripts playground

lint: ## Run ruff linter
	$(RUN) ruff check src tests scripts playground

fix: ## Auto-fix lint violations
	$(RUN) ruff check --fix src tests scripts playground

typecheck: ## Run mypy strict type checking
	$(RUN) mypy src scripts

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

clean: ## Remove caches and build artifacts
	rm -rf .ruff_cache .pytest_cache .mypy_cache dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
