.PHONY: help
help: ## Prints help message.
	@ grep -h -E '^[a-zA-Z0-9_-].+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[1m%-30s\033[0m %s\n", $$1, $$2}'

NEO4J_CONTAINER := neo4j-cdep-test
LOCAL_AI_CONTAINER := local-ai

.PHONY: setup-local-neo4j
setup-local-neo4j: ## Provisions local neo4j db
	@ echo 'Setup local cdep db'
	@ docker rm -f ${NEO4J_CONTAINER} 2> /dev/null
	@ docker run -d --rm \
		--name ${NEO4J_CONTAINER} \
		--publish=7474:7474 --publish=7687:7687 \
		--env=NEO4J_AUTH=none \
		-e NEO4J_apoc_export_file_enabled=true \
		-e NEO4J_apoc_import_file_enabled=true \
		-e NEO4J_apoc_import_file_use__neo4j__config=true \
		-e NEO4J_PLUGINS=\[\"apoc\"\] \
	neo4j:5.26.0-community-ubi9

.PHONY: setup-local-ai
setup-local-ai: ## Provision Local AI for connection
	@ echo 'Setup local AI'
	@ docker rm -f ${LOCAL_AI_CONTAINER} 2> /dev/null
	@ docker run -p 8080:8080 \
 		--name ${LOCAL_AI_CONTAINER} -ti localai/localai:latest

.PHONY: provision-app
provision-app: ## Provision all necessary stuff
	make setup-local-neo4j
	make setup-local-ai

.PHONY: install-local-dependencies
install-local-dependencies: ## Installs local dependencies pytest
	@ pip install -r requirements.txt
	@ pip install pytest

.PHONY: local-test
local-test: ## Runs pytest
	@ pytest test_aws_account_import_.py --vv

.PHONY: clean-local-neo4j
tear-down: ## Tears down local Neo4j database.
	@ docker rm -f ${NEO4J_CONTAINER} 2> /dev/null