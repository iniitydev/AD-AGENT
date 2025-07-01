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

# --- Rebranding Phase Targets ---
# Note: The `sed -i` command below is for GNU sed. For macOS/BSD sed, it might need `sed -i ''`.
# This target is a helper and assumes a SECRET_KEY exists in the .env file.
# Actual rotation of external service keys is a manual process.
rotate-secrets:
	@echo "🔑 Generating new example SECRET_KEY..."
	@python -c "import secrets; print(f'NEW_EXAMPLE_SECRET_KEY={secrets.token_urlsafe(48)}')" > .env.new.example
	@echo "   New example key written to .env.new.example."
	@echo "   To apply to your .env file (if it contains SECRET_KEY=...):"
	@echo "   1. Review .env.new.example"
	@echo "   2. Manually update or use: sed -i 's/^SECRET_KEY=.*/SECRET_KEY_NEEDS_UPDATE_FROM_NEW_EXAMPLE/' .env && echo 'SECRET_KEY updated line marked in .env'"
	@echo "      (Adjust sed command for your OS if not Linux. Be cautious with direct file edits.)"
	@echo ""
	@echo "‼️ IMPORTANT: MANUALLY ROTATE THESE EXTERNAL SECRETS/KEYS:"
	@echo "   1. Cloud Provider Access Keys (AWS/Azure/GCP)"
	@echo "   2. CI/CD Pipeline Tokens (GitHub Actions secrets, etc.)"
	@echo "   3. Database Credentials (if used)"
	@echo "   4. External API Keys (e.g., Pinata for IPFS if used in future)"
	@echo "   5. Any other sensitive credentials used by the application or deployment."
	@echo ""
	@echo "   After updating .env and external services, you can remove .env.new.example."
	@echo "Secrets rotation reminders complete. Manual action required for full security."
