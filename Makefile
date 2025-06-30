.PHONY: help up down logs shell test lint format clean verify-integrity manifest train predict serve
.DEFAULT_GOAL := help

help:
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  up                Build and start services in detached mode."
	@echo "  down              Stop and remove services."
	@echo "  serve             Start the API server inside the container."
	@echo "  logs              Follow logs for the agent service."
	@echo "  shell             Start a bash shell inside the agent container."
	@echo "  test              Run pytest for all tests."
	@echo "  lint              Run flake8 linter on the source code."
	@echo "  format            Format code with black."
	@echo "  manifest          (Re)generate the sovereign_manifest.json file."
	@echo "  verify-integrity  Verify the integrity of the codebase against the manifest."
	@echo "  train             Run the model training process inside the container."
	@echo "  predict           Run model prediction on the input data inside the container."
	@echo "  clean             Stop services and remove all volumes (data loss!)."

up:
	docker-compose up --build -d

down:
	docker-compose down

serve:
	docker-compose exec agent python -m src.main serve

logs:
	docker-compose logs -f agent

shell:
	docker-compose exec agent bash

test:
	docker-compose exec agent pytest tests/ --cov=src

lint:
	docker-compose exec agent flake8 src/ tests/

format:
	docker-compose exec agent black src/ tests/

# Target to generate the manifest using the script directly
manifest:
	docker-compose exec agent python scripts/verify_integrity.py generate

# Target to verify integrity using the script directly
verify-integrity-script: # Renamed to be specific
	docker-compose exec agent python scripts/verify_integrity.py verify

# Target to verify integrity using the main CLI's verify command
verify:
	docker-compose exec agent python -m src.main verify

train:
	docker-compose exec agent python -m src.main train

predict:
	docker-compose exec agent python -m src.main predict

clean:
	docker-compose down -v --remove-orphans
