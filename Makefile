# Makefile for AdventureLog project
DOCKER_COMPOSE = docker compose -f docker-compose.yml
DOCKER_COMPOSE_TRAEFIK = docker compose -f docker-compose-traefik.yaml

.PHONY: help
help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

all: dev ## Build all services (alias for dev)

download-countries: ## Download countries
	@cd backend/server && mkdir -p media
	@cd backend/server && python manage.py download-countries --force
	@echo "Countries downloaded"

download-cities: ## Download cities
	@cd backend/server && mkdir -p media/cities_data
	@cd backend/server && python manage.py cities --import=country
	# @cd backend/server && python manage.py cities --import=region
	# @cd backend/server && python manage.py cities --import=city
	@cd backend/server && python manage.py cities --import=alt_name
	@echo "Cities downloaded"

import-translations: ## Import translations
	@cd backend/server && python manage.py get-translations
	@echo "Translations Imported"

dev-db: dev ## Start development database
	@if [ ! "$$(docker ps -q -f name=adventurelog-development)" ]; then \
		if [ "$$(docker ps -aq -f status=exited -f name=adventurelog-development)" ]; then \
			docker rm adventurelog-development; \
		fi; \
		docker run --name adventurelog-development \
			-e POSTGRES_USER=admin \
			-e POSTGRES_PASSWORD=admin \
			-e POSTGRES_DB=adventurelog \
			-p 5432:5432 \
			-d postgis/postgis:15-3.3; \
		echo "Development database started. Please wait a few seconds for it to initialize."; \
		echo "Please update the backend/.env file with these credentials:"; \
		echo "PGHOST=localhost"; \
		echo "PGDATABASE=adventurelog"; \
		echo "PGUSER=admin"; \
		echo "PGPASSWORD=admin"; \
	else \
		echo "Development database is already running."; \
	fi

web: dev ## Start web service
	@cd frontend && pnpm dev

django: dev ## Start Django server
	@cd backend/server && python manage.py migrate
	@cd frontend && pnpm django

dev: ## Setup Development Environment
	@[ -f backend/server/.env ] || cp backend/server/.env.example backend/server/.env
	@[ -f frontend/.env ] || cp frontend/.env.example frontend/.env
	@cd frontend && pnpm install 
	@[ -d .venv ] || python -m venv .venv
	. .venv/bin/activate
	@pip install -r backend/server/requirements.txt


