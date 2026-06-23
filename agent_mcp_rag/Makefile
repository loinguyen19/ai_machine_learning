PYTHON ?= python3
PROJECT_ROOT := $(abspath .)
VENV_DIR := $(PROJECT_ROOT)/.venv
VENV_PYTHON := $(VENV_DIR)/bin/python

.PHONY: help venv install activate reinstall clean-venv seed-memory run-agent clean

help: ## Prints help message.
	@ grep -h -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[1m%-30s\033[0m %s\n", $$1, $$2}'

venv: ## Create local .venv (if missing)
	@test -d $(VENV_DIR) || $(PYTHON) -m venv $(VENV_DIR)
	@$(VENV_PYTHON) -m pip install --upgrade pip

install: venv ## Install dependencies into agent_mcp_rag/.venv
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@echo "Installed. Activate with: source .venv/bin/activate"

activate: ## Print activation command for this project's .venv
	@echo "source $(VENV_DIR)/bin/activate"

reinstall: clean-venv install ## Recreate .venv and reinstall

clean-venv: ## Remove local .venv
	rm -rf $(PROJECT_ROOT)/.venv

seed-memory: install ## Seed mock chat history into Chroma vector store
	cd src && $(VENV_PYTHON) -m rag.seed_history --force

run-agent: install ## Run the holiday planner agent
	cd src && $(VENV_PYTHON) agent.py

clean: ## Remove generated chroma data and artifacts (keeps mock_chat_history.json)
	rm -rf data/chroma artifacts final_plan
	@ echo "Cleaned generated data (kept mock_chat_history.json)"
