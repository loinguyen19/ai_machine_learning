PYTHON ?= python3
PROJECT_ROOT := $(abspath .)
VENV_DIR := $(PROJECT_ROOT)/.venv
VENV_PYTHON := $(VENV_DIR)/bin/python

.PHONY: help venv install activate reinstall clean-venv run-agent

help: ## Show available targets
	@ grep -h -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[1m%-24s\033[0m %s\n", $$1, $$2}'

venv: ## Create local .venv (if missing)
	@test -d $(VENV_DIR) || $(PYTHON) -m venv $(VENV_DIR)
	@$(VENV_PYTHON) -m pip install --upgrade pip

install: venv ## Install dependencies into agent_with_tools/.venv
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@echo "Installed. Activate with: source .venv/bin/activate"

activate: ## Print activation command for this project's .venv
	@echo "source $(VENV_DIR)/bin/activate"

reinstall: clean-venv install ## Recreate .venv and reinstall

clean-venv: ## Remove local .venv
	rm -rf $(VENV_DIR)

run-agent: install ## Run the search agent (interactive if no question passed)
	cd src && $(VENV_PYTHON) agent.py $(ARGS)
