.PHONY: build up down logs shell migrate makemigrations createsuperuser test lint format

# Build all containers
build:
	docker compose build

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# Open a shell in the web container
shell:
	docker compose exec web python manage.py shell

# Open a bash shell in the web container
bash:
	docker compose exec web bash

# Run migrations
migrate:
	docker compose exec web python manage.py migrate

# Create migrations
makemigrations:
	docker compose run --rm --no-deps --entrypoint "" web python manage.py makemigrations

# Create superuser
createsuperuser:
	docker compose exec web python manage.py createsuperuser

# Run tests
test:
	docker compose exec web pytest --cov=apps --cov-report=term-missing -v

# Run linter
lint:
	docker compose exec web ruff check .

# Format code
format:
	docker compose exec web ruff format .

# Run full CI locally (lint + test)
ci: lint test

# First-time setup: build, start, and run initial migrations
setup: build up
	docker compose exec web python manage.py makemigrations
	docker compose exec web python manage.py migrate
	@echo "Setup complete! Create a superuser with: make createsuperuser"

