PYTHON ?= python3
PROJECT_ROOT := $(abspath ..)
REPO_ROOT := $(abspath ../..)
VENV_DIR := $(PROJECT_ROOT)/.venv
VENV_PYTHON := $(VENV_DIR)/bin/python
CHEMISTRY_ROOT := $(abspath .)

.PHONY: help venv install activate reinstall clean-venv run-api test

help: ## Show available targets
	@ grep -h -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[1m%-24s\033[0m %s\n", $$1, $$2}'

venv: ## Create .venv in ai_agent_video_generation/ (if missing)
	@test -d $(VENV_DIR) || $(PYTHON) -m venv $(VENV_DIR)
	@$(VENV_PYTHON) -m pip install --upgrade pip

install: venv ## Install dependencies into ai_agent_video_generation/.venv
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@echo "Installed. Activate with: source ../.venv/bin/activate"

activate: ## Print activation command for the parent .venv
	@echo "source $(VENV_DIR)/bin/activate"

reinstall: clean-venv install ## Recreate .venv and reinstall

clean-venv: ## Remove ai_agent_video_generation/.venv
	rm -rf $(VENV_DIR)

run-api: install ## Run FastAPI server (reload) on http://localhost:8000
	cd $(CHEMISTRY_ROOT) && PYTHONPATH=$(REPO_ROOT) $(VENV_PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test: install ## Run pytest suite
	cd $(CHEMISTRY_ROOT) && PYTHONPATH=$(REPO_ROOT) $(VENV_PYTHON) -m pytest -q tests
