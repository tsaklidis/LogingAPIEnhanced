# Home Sensor Platform — Architecture Proposal

## Table of Contents

- [Overview](#overview)
- [Lessons from LogingAPI](#lessons-from-logingapi)
- [Tech Stack](#tech-stack)
- [Database Design](#database-design)
- [Authentication Strategy](#authentication-strategy)
- [API Endpoints](#api-endpoints)
- [Performance & Caching](#performance--caching)
- [Project Structure](#project-structure)
- [Docker Setup](#docker-setup)
- [CI/CD](#cicd)
- [Testing](#testing)
- [Additional Improvements](#additional-improvements)

---

## Overview

A high-performance REST API for collecting, storing, and querying data from home IoT sensors (temperature, humidity, battery, etc.). Built for high ingestion throughput, flexible sensor payloads, and clean separation between human users and device authentication.

---

## Lessons from LogingAPI

### Patterns Worth Keeping

| Pattern | Implementation |
|---------|---------------|
| UUIDs as public identifiers | Avoids enumeration attacks, used as PKs |
| Public/open endpoints | `is_public` flag on Space model + `/api/v1/public/` namespace |
| Bulk ingestion endpoint | `/ingest/bulk/` for offline batch-and-flush devices |
| Backfill with custom timestamp | `recorded_at` field (validated: not future, max 30 days old) |
| Rich date/time filtering | `django-filter` on single `recorded_at` DateTimeField |
| `/latest/` endpoint for dashboards | Served from Redis cache, zero DB queries |
| Owner-scoped permissions | Permission chain: `sensor → space → home → user` |

### Problems Fixed

| Issue | Fix |
|-------|-----|
| Custom token auth (username+password in POST body) | SimpleJWT for humans + `X-Sensor-Key` header for devices |
| Single-value measurements (1 row = 1 metric) | JSONField packet-per-row (1 row = full sensor reading) |
| Split date/time fields | Single `DateTimeField` with proper indexing |
| Hand-rolled query param filtering | `django-filter` with `IsoDateTimeFilter` + lookups |
| No API versioning | URL versioning (`/api/v1/`) from day one |
| No rate limiting | DRF throttling on ingestion endpoints |
| No schema documentation | `drf-spectacular` for OpenAPI/Swagger |
| No tests mentioned | Full pytest suite with factory_boy fixtures |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Django 5 LTS |
| API Layer | Django REST Framework |
| Auth (users) | SimpleJWT (access + refresh tokens) |
| Auth (devices) | Custom `X-Sensor-Key` header authentication |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Task Queue | Celery |
| App Server | uWSGI |
| Reverse Proxy | Nginx |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Testing | pytest + pytest-django + factory_boy |
| Linting | ruff + mypy |
| API Docs | drf-spectacular (OpenAPI 3.1 + Swagger UI) |
| Filtering | django-filter |

---

## Database Design

```python
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Extended user model for future fields (notification prefs, etc.)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)


class Home(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="homes")
    name = models.CharField(max_length=128)
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["owner"])]


class Space(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    home = models.ForeignKey(Home, on_delete=models.CASCADE, related_name="spaces")
    name = models.CharField(max_length=128)  # "Living Room", "Bedroom", "Balcony"
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Sensor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name="sensors")
    name = models.CharField(max_length=128)
    sensor_type = models.CharField(max_length=64)  # "DHT22", "BME280", "BMP180"
    api_key = models.CharField(max_length=64, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SensorReading(models.Model):
    """
    One row = one full data packet from a sensor.
    Uses PostgreSQL JSONField for flexible, schema-less payloads.

    Example data: {"temperature": 25.6, "humidity": 48.2, "battery_percentage": 35, "battery_voltage": 3.2}
    """

    id = models.BigAutoField(primary_key=True)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="readings")
    data = models.JSONField()
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["sensor", "-recorded_at"]),
        ]
```

### Design Decisions

- **JSONField for `data`** — no migrations needed for new sensor metrics, one INSERT per reading
- **BigAutoField** — supports billions of rows
- **Composite index `(sensor, -recorded_at)`** — optimizes the most common query pattern
- **Consider PostgreSQL table partitioning** (by month) on `SensorReading` when data exceeds ~100M rows

---

## Authentication Strategy

### Three Separate Audiences

| Audience | Method | Lifetime | Use Case |
|----------|--------|----------|----------|
| Humans / Dashboards | SimpleJWT (access + refresh) | 15 min / 7 days | Web UI, mobile apps, management |
| Individual IoT Sensors | `X-Sensor-Key` header | Long-lived, rotatable | Direct data ingestion from WiFi sensors |
| Central Gateway Devices | `X-Gateway-Key` header | Long-lived, rotatable | Batch ingestion from a hub (RPi, HA) for all sensors in a home |

### JWT Configuration

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
```

### Sensor Key Authentication

```python
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class SensorKeyAuthentication(BaseAuthentication):
    """
    IoT devices send: X-Sensor-Key: <key>
    No username/password needed on the device.
    """

    def authenticate(self, request):
        key = request.headers.get("X-Sensor-Key")
        if not key:
            return None
        try:
            sensor = Sensor.objects.select_related("space__home__owner").get(api_key=key, is_active=True)
        except Sensor.DoesNotExist:
            raise AuthenticationFailed("Invalid or inactive sensor key")
        # Return (user, auth_info) — DRF convention
        return (sensor.space.home.owner, sensor)
```

### Key Rotation

Users can rotate a compromised sensor key without re-registering the sensor:

```
POST /api/v1/sensors/{uuid}/rotate-key/
```

---

## API Endpoints

### Auth (Users)

```
POST   /api/v1/auth/token/                  # Obtain JWT pair
POST   /api/v1/auth/token/refresh/           # Refresh access token
```

### Management (JWT-auth, owner-scoped)

```
GET|POST       /api/v1/homes/
GET|PUT|DELETE  /api/v1/homes/{uuid}/
GET|POST       /api/v1/homes/{uuid}/spaces/
GET|PUT|DELETE  /api/v1/spaces/{uuid}/
GET|POST       /api/v1/spaces/{uuid}/sensors/
GET|PUT|DELETE  /api/v1/sensors/{uuid}/
POST           /api/v1/sensors/{uuid}/rotate-key/
POST           /api/v1/homes/{uuid}/gateway-key/     # Generate/rotate gateway key
DELETE         /api/v1/homes/{uuid}/gateway-key/     # Revoke gateway key
```

### Ingestion (X-Sensor-Key auth — per-sensor)

```
POST   /api/v1/ingest/                       # Single packet
POST   /api/v1/ingest/bulk/                  # List of packets (offline batch)
```

**Single packet request:**
```json
{
  "data": {"temperature": 25.6, "humidity": 48.2, "battery_voltage": 3.2},
  "recorded_at": "2026-07-16T10:30:00Z"
}
```

**Bulk request:**
```json
[
  {"data": {"temperature": 25.6, "humidity": 48.2}, "recorded_at": "2026-07-16T10:30:00Z"},
  {"data": {"temperature": 25.8, "humidity": 47.9}, "recorded_at": "2026-07-16T10:31:00Z"}
]
```

### Ingestion (X-Gateway-Key auth — home-level, multi-sensor)

```
POST   /api/v1/ingest/gateway/               # Multiple sensors in one request
```

**Gateway request:**
```json
{
  "readings": [
    {"sensor_id": "uuid-of-sensor-1", "data": {"temperature": 25.6, "humidity": 48.2}},
    {"sensor_id": "uuid-of-sensor-2", "data": {"co2": 412, "tvoc": 15}},
    {"sensor_id": "uuid-of-sensor-1", "data": {"temperature": 25.8}, "recorded_at": "2026-07-16T10:31:00Z"}
  ]
}
```

> `recorded_at` is optional (defaults to server time). Validated: not in future, max 30 days backfill.

### Readings (JWT-auth, owner-scoped)

```
GET    /api/v1/sensors/{uuid}/readings/
           ?from=2026-07-01T00:00:00Z
           &to=2026-07-16T00:00:00Z
           &order_by=-recorded_at
           &limit=100

GET    /api/v1/sensors/{uuid}/readings/latest/
```

### Public (no auth, only if `space.is_public = True`)

```
GET    /api/v1/public/sensors/{uuid}/readings/
GET    /api/v1/public/sensors/{uuid}/readings/latest/
```

---

## Performance & Caching

### Redis Caching Strategy

```python
# On every ingestion, cache the latest reading per sensor
cache.set(f"sensor:{sensor_id}:latest", serialized_data)  # No TTL, always overwritten

# GET /sensors/{uuid}/readings/latest/ → reads from Redis, zero DB queries
cached = cache.get(f"sensor:{sensor_id}:latest")
if cached:
    return Response(cached)
```

### Ingestion Optimization

- **`bulk_create()`** for batch ingestion (single INSERT for N readings)
- **Minimal serializer** on ingestion path — validate only, skip read-back serialization
- **No `select_related` / `prefetch_related` on write path**
- **Connection pooling** via `django-db-connection-pool` or pgBouncer

### Throttling

```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "ingestion": "60/min",  # Per sensor key
        "readings": "120/min",  # Per user
        "management": "30/min",  # Per user
    },
}
```

### Background Tasks (Celery)

- **Data retention** — aggregate old readings into hourly/daily averages after 30/90 days
- **Alerts** — notify user if sensor stops reporting (dead sensor detection)
- **Cleanup** — rotate expired JWT blacklist entries

---

## Project Structure

```
home-sensor-platform/
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── celery.py
│   └── uwsgi.ini
├── apps/
│   ├── __init__.py
│   ├── accounts/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── homes/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py
│   │   └── admin.py
│   ├── sensors/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── authentication.py    # SensorKeyAuthentication
│   │   ├── filters.py           # django-filter FilterSets
│   │   ├── tasks.py             # Celery tasks
│   │   └── admin.py
│   └── common/
│       ├── pagination.py
│       ├── permissions.py
│       └── mixins.py
├── tests/
│   ├── conftest.py              # pytest fixtures, factory_boy factories
│   ├── factories.py
│   ├── test_auth.py
│   ├── test_homes.py
│   ├── test_ingestion.py
│   ├── test_readings.py
│   └── test_public.py
└── nginx/
    └── nginx.conf
```

---

## Docker Setup

```yaml
# docker-compose.yml
services:
  web:
    build: .
    command: uwsgi --ini config/uwsgi.ini
    volumes:
      - .:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    env_file: .env
    expose:
      - "8000"

  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru

  celery:
    build: .
    command: celery -A config worker -l info --concurrency=2
    depends_on: [db, redis]
    env_file: .env

  celery-beat:
    build: .
    command: celery -A config beat -l info
    depends_on: [db, redis]
    env_file: .env

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - web

volumes:
  pgdata:
```

---

## CI/CD

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff mypy
      - run: ruff check .
      - run: ruff format --check .

  test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_sensors
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements/dev.txt
      - run: pytest --cov=apps --cov-report=xml -v
        env:
          DATABASE_URL: postgres://test:test@localhost:5432/test_sensors
          REDIS_URL: redis://localhost:6379/0
          DJANGO_SETTINGS_MODULE: config.settings.test
      - uses: codecov/codecov-action@v4
        with:
          file: coverage.xml
```

### `.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push Docker image
        run: |
          docker build -t ghcr.io/${{ github.repository }}:latest .
          echo "${{ secrets.GHCR_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push ghcr.io/${{ github.repository }}:latest
      - name: Deploy to server
        run: |
          ssh ${{ secrets.DEPLOY_HOST }} "cd /opt/sensor-platform && docker compose pull && docker compose up -d"
```

---

## Testing

### Strategy

```python
# tests/conftest.py
import pytest
from rest_framework.test import APIClient
from tests.factories import UserFactory, HomeFactory, SpaceFactory, SensorFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    user = UserFactory()
    api_client.force_authenticate(user=user)
    api_client.user = user
    return api_client


@pytest.fixture
def sensor_with_key():
    """A sensor ready for ingestion tests."""
    sensor = SensorFactory()
    return sensor
```

### Test Coverage Targets

| Area | Priority | What to test |
|------|----------|--------------|
| Ingestion | Critical | Single/bulk write, `recorded_at` validation, invalid payloads |
| Auth | Critical | JWT flow, sensor key auth, key rotation, expired tokens |
| Permissions | High | Owner can't access other's homes, public vs private |
| Readings | High | Filtering, pagination, `/latest/` cache hit |
| Throttling | Medium | Rate limit triggers correctly |

---

## Additional Improvements

1. **Data Retention Policy** — Celery beat task aggregates readings older than 30 days into hourly averages, deletes raw rows after 90 days (configurable per home)

2. **Health Check Endpoint** — `GET /api/v1/health/` returns DB + Redis connectivity status (for Docker healthchecks and monitoring)

3. **Dead Sensor Detection** — Celery periodic task checks if any active sensor hasn't reported in N minutes, flags it and optionally notifies owner

4. **WebSocket Support (future)** — Django Channels for real-time dashboard updates (subscribe to sensor readings)

5. **Pre-commit Hooks** — ruff, mypy, pytest (fast subset) on every commit

6. **Environment Configuration** — `django-environ` for 12-factor app config from `.env`

7. **Database Connection Pooling** — pgBouncer or `django-db-connection-pool` for handling connection storms from uWSGI workers

8. **Structured Logging** — `structlog` with JSON output for easy parsing in production (ELK/Loki)

---

## Summary

This architecture delivers a production-ready, high-performance sensor data platform that:

- Cleanly separates human and device authentication
- Handles high ingestion load with minimal DB overhead (JSON packets, bulk inserts, Redis caching)
- Is fully containerized and CI/CD-ready from day one
- Maintains the good patterns from LogingAPI while fixing its architectural shortcomings
- Is extensible for future needs (real-time, alerts, data aggregation)