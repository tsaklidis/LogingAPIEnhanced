# Development Guide

## Prerequisites

- Docker & Docker Compose (recommended), **or**
- Python 3.12+, PostgreSQL 16, Redis 7

---

## Quick Start (Docker)

```bash
# 1. Clone and enter the project
cd LogingAPIEnchanched

# 2. Create .env file
cp .env.example .env   # or create manually (see Environment Variables below)

# 3. Build, start, and run initial migrations
make setup

# 4. Create an admin user
make createsuperuser

# 5. Visit
#   API:     http://localhost/api/v1/
#   Swagger: http://localhost/api/docs/
#   Admin:   http://localhost/admin/
```

## Quick Start (Local / No Docker)

```bash
# 1. Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements/dev.txt

# 3. Set environment
export DJANGO_SETTINGS_MODULE=config.settings.dev

# 4. Start PostgreSQL and Redis (e.g., via Homebrew on macOS)
brew services start postgresql@16
brew services start redis

# 5. Create database
createdb sensor_platform

# 6. Run migrations
python manage.py migrate

# 7. Create superuser
python manage.py createsuperuser

# 8. Start dev server
python manage.py runserver
```

---

## Docker Services

| Service | Purpose | Port |
|---------|---------|------|
| `web` | Django app (uWSGI) | 8000 (internal) |
| `db` | PostgreSQL 16 | 5432 (internal) |
| `redis` | Cache + Celery broker | 6379 (internal) |
| `celery` | Background task worker | — |
| `celery-beat` | Periodic task scheduler | — |
| `nginx` | Reverse proxy | **80** (exposed) |

### Docker Compose Override

`docker-compose.override.yml` exists for local dev customizations (e.g., extra port mappings, volume mounts). It is auto-loaded by Docker Compose.

---

## Make Targets

| Command | Description |
|---------|-------------|
| `make build` | Build all Docker images |
| `make up` | Start all services in background |
| `make down` | Stop all services |
| `make logs` | Tail logs from all services |
| `make shell` | Django Python shell inside web container |
| `make bash` | Bash shell inside web container |
| `make migrate` | Run `python manage.py migrate` |
| `make makemigrations` | Run `python manage.py makemigrations` |
| `make createsuperuser` | Create a Django admin superuser |
| `make test` | Run pytest with coverage |
| `make lint` | Run ruff linter |
| `make format` | Auto-format code with ruff |
| `make ci` | Run lint + test (mirrors CI pipeline) |
| `make setup` | First-time setup: build + start + migrate |

---

## Environment Variables

Create a `.env` file in the project root. Required variables:

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=sensor_platform
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db          # Use 'localhost' when running without Docker
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0        # Use 'redis://localhost:6379/0' without Docker

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# JWT (optional — defaults shown)
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

> **Note:** When running with Docker, service hostnames are `db` and `redis`. When running locally, use `localhost`.

---

## Settings Modules

| Module | When Used | Key Differences |
|--------|-----------|-----------------|
| `config.settings.base` | Always imported | All shared config |
| `config.settings.dev` | Local development | `DEBUG=True`, throttling disabled |
| `config.settings.test` | `pytest` runs | In-memory cache, eager Celery, MD5 password hasher, throttling disabled |
| `config.settings.prod` | Production | Production-hardened settings |

Set the active module via `DJANGO_SETTINGS_MODULE` env var. Default for tests is configured in `pytest.ini`.

---

## Running Tests

```bash
# Docker
make test

# Local
pytest                              # Uses config.settings.test (from pytest.ini)
pytest --cov=apps --cov-report=html # With HTML coverage report
pytest tests/test_ingestion.py -v   # Single test file
pytest -k "test_bulk"               # Filter by test name
```

### Test Configuration (`pytest.ini`)

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests.py test_*.py *_tests.py
addopts = -v --tb=short
```

---

## Linting & Formatting

```bash
# Check for issues
ruff check .

# Auto-fix what's possible
ruff check --fix .

# Format code
ruff format .

# Check formatting without changing files
ruff format --check .
```

Ruff configuration is in `ruff.toml` at the project root.

---

## Database Migrations

```bash
# Create new migrations after model changes
make makemigrations
# or locally:
python manage.py makemigrations

# Apply migrations
make migrate
# or locally:
python manage.py migrate
```

---

## Celery (Background Tasks)

Tasks are defined in `apps/sensors/tasks.py`. Celery beat schedule is in `config/settings/base.py`.

```bash
# Start worker manually (local)
celery -A config worker -l info --concurrency=2

# Start beat scheduler manually (local)
celery -A config beat -l info
```

In Docker, both run as separate services automatically.

---

## API Documentation

Swagger UI is auto-generated by `drf-spectacular`:

- **Swagger UI:** `http://localhost/api/docs/`
- **Raw OpenAPI schema:** `http://localhost/api/schema/`
- **Admin panel:** `http://localhost/admin/`

