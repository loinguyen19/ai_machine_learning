PYTHON ?= python3
PROJECT_ROOT := $(abspath .)
VENV_DIR := $(PROJECT_ROOT)/.venv
VENV_PYTHON := $(VENV_DIR)/bin/python

.PHONY: help venv install activate reinstall clean-venv run-kyc run-support test eval

help: ## Show available targets
	@ grep -h -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[1m%-24s\033[0m %s\n", $$1, $$2}'

venv: ## Create local .venv (if missing)
	@test -d $(VENV_DIR) || $(PYTHON) -m venv $(VENV_DIR)
	@$(VENV_PYTHON) -m pip install --upgrade pip

install: venv ## Install dependencies into finance_agent/.venv
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@echo "Installed. Activate with: source .venv/bin/activate"

activate: ## Print activation command for this project's .venv
	@echo "source $(VENV_DIR)/bin/activate"

reinstall: clean-venv install ## Recreate .venv and reinstall

clean-venv: ## Remove local .venv
	rm -rf $(VENV_DIR)

run-kyc: install ## Run the KYC review agent (CASE_FILE=path optional, needs an LLM API key)
	cd src && $(VENV_PYTHON) kyc_agent.py $(if $(CASE_FILE),--case-file $(CASE_FILE),)

run-support: install ## Run the support triage agent (TICKET_FILE=path optional, needs an LLM API key)
	cd src && $(VENV_PYTHON) support_agent.py $(if $(TICKET_FILE),--ticket-file $(TICKET_FILE),)

test: install ## Run offline unit tests (guardrails + tools) — no API key needed
	$(VENV_PYTHON) -m pytest -v

eval: install ## Run the live end-to-end eval harness (needs an LLM API key)
	cd evals && $(VENV_PYTHON) run_evals.py
