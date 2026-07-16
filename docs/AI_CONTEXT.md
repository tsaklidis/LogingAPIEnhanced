# AI Context — Quick Project Reference

> **Purpose:** This document gives AI coding assistants fast, structured context about the entire codebase. Read this first before making changes.

## What Is This Project?

A **Django REST API** for collecting, storing, and querying data from home IoT sensors (temperature, humidity, battery, etc.). Called **Home Sensor Platform**.

## Tech Summary

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Framework | Django 5.0 + Django REST Framework |
| Auth (humans) | SimpleJWT — `Authorization: Bearer <token>` |
| Auth (sensors) | Custom `X-Sensor-Key` header → `SensorKeyAuthentication` |
| Auth (gateways) | Custom `X-Gateway-Key` header → `GatewayKeyAuthentication` |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Task Queue | Celery (broker: Redis) |
| App Server | uWSGI behind Nginx |
| Containerization | Docker Compose |
| Testing | pytest + pytest-django + factory_boy |
| Linting | ruff |
| API Docs | drf-spectacular (OpenAPI 3.1) |
| Filtering | django-filter |

## Project Layout

```
config/                     # Django project config
  settings/
    base.py                 # All shared settings (DRF, JWT, Celery, caches)
    dev.py                  # DEBUG=True, no throttling
    test.py                 # In-memory cache, eager Celery, MD5 hasher
    prod.py                 # Production overrides
  urls.py                   # Root URL conf — mounts all app URLs under /api/v1/
  celery.py                 # Celery app
  uwsgi.ini                # uWSGI config

apps/
  accounts/                 # User model + registration + profile
    models.py               # User(AbstractUser) with UUID PK
    serializers.py          # UserSerializer, UserRegistrationSerializer
    views.py                # UserRegistrationView, UserProfileView
    urls.py                 # /auth/token/, /auth/register/, /auth/profile/

  homes/                    # Home + Space management
    models.py               # Home (has gateway key fields), Space (has is_public)
    serializers.py          # HomeSerializer, HomeListSerializer, SpaceSerializer
    views.py                # CRUD for Home and Space
    permissions.py          # IsHomeOwner
    urls.py                 # /homes/, /homes/<uuid>/, /homes/<uuid>/spaces/, /spaces/<uuid>/

  sensors/                  # Sensor CRUD, data ingestion, readings
    models.py               # Sensor (has key_prefix + key_hash), SensorReading (JSONField data)
    serializers.py          # SensorSerializer, IngestSerializer, BulkIngestSerializer, GatewayIngestSerializer
    views.py                # IngestView, BulkIngestView, GatewayIngestView, readings views, key rotation
    authentication.py       # SensorKeyAuthentication, GatewayKeyAuthentication
    filters.py              # SensorReadingFilter (from_date, to_date)
    permissions.py          # IsSensorOwner, IsSensorPublic
    tasks.py                # detect_dead_sensors, cleanup_old_readings
    urls.py                 # /ingest/, /ingest/bulk/, /ingest/gateway/, /sensors/<uuid>/readings/

  common/                   # Shared utilities
    apikey.py               # generate_key(), verify_key(), parse_prefix() — prefix.secret format
    pagination.py           # StandardPagination (page_size=50, max=1000)
    permissions.py          # IsOwnerOrReadOnly
    mixins.py               # OwnerFilterMixin
    views.py                # HealthCheckView — checks DB + Redis
    urls.py                 # /health/

tests/                      # All tests
  conftest.py               # Pytest fixtures (api_client, user, home, space, sensor, gateway_setup)
  factories.py              # factory_boy factories (UserFactory, HomeFactory, SensorFactory, etc.)
  test_auth.py              # JWT auth + registration tests
  test_homes.py             # Home/Space CRUD tests
  test_ingestion.py         # Single/bulk/gateway ingestion tests
  test_readings.py          # Reading list/filter/latest tests
  test_public.py            # Public sensor access tests
  test_gateway.py           # Gateway key management tests
```

## Data Model (Entity Relationships)

```
User (UUID PK, AbstractUser)
  └── Home (UUID PK, owner FK → User)
        ├── gateway key: key_prefix + key_hash (for X-Gateway-Key auth)
        └── Space (UUID PK, home FK → Home, is_public bool)
              └── Sensor (UUID PK, space FK → Space)
                    ├── sensor key: key_prefix + key_hash (for X-Sensor-Key auth)
                    └── SensorReading (BigAutoField PK, sensor FK → Sensor)
                          ├── data: JSONField (flexible payload)
                          └── recorded_at: DateTimeField (indexed with sensor)
```

**Ownership chain:** `SensorReading → Sensor → Space → Home → User`

## API Key Security Model

Keys use a **prefix.secret** format:
- **prefix** (8 chars): stored in DB, indexed, used for fast lookup
- **secret** (48 chars): never stored; only the SHA-256 hash of the full `prefix.secret` is stored
- Verification uses `hmac.compare_digest` (constant-time) to prevent timing attacks
- Raw key is shown **once** at creation time, never retrievable again

See `apps/common/apikey.py` for implementation.

## Authentication Flow Summary

| Endpoint Group | Auth Class | Header | `request.user` | `request.auth` |
|---------------|-----------|--------|----------------|----------------|
| Management (homes, spaces, sensors) | `JWTAuthentication` | `Authorization: Bearer <jwt>` | `User` | JWT token |
| Per-sensor ingestion (`/ingest/`, `/ingest/bulk/`) | `SensorKeyAuthentication` | `X-Sensor-Key: <key>` | Home owner `User` | `Sensor` instance |
| Gateway ingestion (`/ingest/gateway/`) | `GatewayKeyAuthentication` | `X-Gateway-Key: <key>` | Home owner `User` | `Home` instance |
| Public readings | None (AllowAny) | — | Anonymous | — |

## Caching Strategy

- On every ingestion, the latest reading per sensor is cached in Redis: `sensor:<uuid>:latest`
- `GET /sensors/<uuid>/readings/latest/` reads from cache first — zero DB queries on cache hit
- Cache has no TTL — it's overwritten on every new ingestion

## Celery Tasks

| Task | Schedule | What It Does |
|------|----------|-------------|
| `detect_dead_sensors` | Every 5 min | Flags sensors with no readings in 15 min |
| `cleanup_old_readings` | Every 1 hour | Deletes raw readings older than 90 days |

## Throttle Scopes

| Scope | Rate | Applied To |
|-------|------|-----------|
| `ingestion` | 60/min | Ingest, bulk ingest, gateway ingest |
| `readings` | 120/min | Reading list, latest reading |
| `management` | 30/min | Home/Space/Sensor CRUD, key rotation |

Throttling is **disabled** in `dev.py` and `test.py` settings.

## Key Conventions

1. **All PKs are UUIDs** except `SensorReading` which uses `BigAutoField`
2. **Owner scoping**: every queryset filters by `request.user` through the ownership chain
3. **Serializer split**: list views often use a lighter serializer (e.g., `HomeListSerializer` vs `HomeSerializer`)
4. **`recorded_at` validation**: cannot be in the future, max 30 days backfill
5. **Bulk limit**: max 1000 readings per bulk/gateway request
6. **URL versioning**: all API endpoints are under `/api/v1/`
7. **Settings are split**: `base.py` → `dev.py` / `test.py` / `prod.py`

## Running the Project

```bash
# Docker (recommended)
make setup              # Build + start + migrate
make test               # Run tests
make lint               # Ruff check

# Local (requires PostgreSQL + Redis)
pip install -r requirements/dev.txt
DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py runserver
pytest                  # Uses config.settings.test
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `insecure-dev-key-...` | Django secret key |
| `DEBUG` | `False` | Debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `DB_NAME` | `sensor_platform` | PostgreSQL database |
| `DB_USER` | `postgres` | PostgreSQL user |
| `DB_PASSWORD` | `postgres` | PostgreSQL password |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for caching |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery results |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | `15` | JWT access token TTL |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | `7` | JWT refresh token TTL |

