# Home Sensor Platform API

A high-performance REST API for collecting, storing, and querying data from home IoT sensors (temperature, humidity, battery, etc.).

Built with **Django 5**, **Django REST Framework**, **PostgreSQL**, **Redis**, and **Celery**.

## Features

- **Three authentication modes** — JWT for humans, per-sensor API keys for IoT devices, per-home gateway keys for central hubs
- **Flexible sensor payloads** — JSON data field accepts any key/value pairs, no migrations needed for new metrics
- **High-throughput ingestion** — single, bulk (up to 1000), and multi-sensor gateway endpoints
- **Real-time latest readings** — served from Redis cache with zero DB queries
- **Public sensors** — optionally expose sensor data without authentication
- **Background tasks** — dead sensor detection, old data cleanup via Celery
- **OpenAPI documentation** — auto-generated Swagger UI via drf-spectacular
- **Fully containerized** — Docker Compose with PostgreSQL, Redis, Celery, Nginx

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/LogingAPIEnchanched.git
cd LogingAPIEnchanched

# 2. Copy environment file
cp .env.example .env

# 3. Build and start (Docker)
make setup

# 4. Create an admin user
make createsuperuser
```

The API is available at `http://localhost/api/v1/` and Swagger docs at `http://localhost/api/docs/`.

## API Overview

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/v1/auth/register/` | None | Register a user |
| `POST /api/v1/auth/token/` | None | Obtain JWT tokens |
| `GET/POST /api/v1/homes/` | JWT | Manage homes |
| `GET/POST /api/v1/homes/{id}/spaces/` | JWT | Manage spaces |
| `GET/POST /api/v1/spaces/{id}/sensors/` | JWT | Manage sensors |
| `POST /api/v1/ingest/` | `X-Sensor-Key` | Ingest single reading |
| `POST /api/v1/ingest/bulk/` | `X-Sensor-Key` | Ingest batch readings |
| `POST /api/v1/ingest/gateway/` | `X-Gateway-Key` | Multi-sensor gateway ingest |
| `GET /api/v1/sensors/{id}/readings/` | JWT | Query historical readings |
| `GET /api/v1/sensors/{id}/readings/latest/` | JWT | Latest reading (cached) |
| `GET /api/v1/public/sensors/{id}/readings/` | None | Public sensor data |
| `GET /api/v1/health/` | None | Health check |

See [docs/USAGE.md](docs/USAGE.md) for the complete user journey with curl examples.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Django 5 + Django REST Framework |
| Auth | SimpleJWT + custom API key auth |
| Database | PostgreSQL 16 |
| Cache & Broker | Redis 7 |
| Task Queue | Celery |
| App Server | uWSGI |
| Reverse Proxy | Nginx |
| API Docs | drf-spectacular (OpenAPI 3.1) |
| Testing | pytest + factory_boy |
| Linting | ruff |

## Project Structure

```
config/                 # Django settings, URLs, Celery, WSGI
  settings/             # base.py / dev.py / test.py / prod.py
apps/
  accounts/             # User model, registration, profile
  homes/                # Home and Space management
  sensors/              # Sensors, ingestion, readings, Celery tasks
  common/               # Shared utilities (API keys, pagination, health check)
tests/                  # pytest test suite with factory_boy
docs/                   # Architecture, usage guide, and reference docs
nginx/                  # Nginx reverse proxy config
requirements/           # Dependency files (base / dev / prod)
```

## Development

```bash
# Run tests
make test

# Lint
make lint

# Format
make format

# Run full CI locally
make ci
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the complete development guide.

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, decisions, and proposals |
| [USAGE.md](docs/USAGE.md) | End-to-end user journey with curl examples |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, Docker, Make targets, env vars |
| [MODELS.md](docs/MODELS.md) | Data model reference with all fields and relationships |
| [API_ENDPOINTS.md](docs/API_ENDPOINTS.md) | Complete endpoint reference |
| [TESTING.md](docs/TESTING.md) | Test guide, fixtures, factories, patterns |
| [AI_CONTEXT.md](docs/AI_CONTEXT.md) | Quick-reference for AI coding assistants |

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

