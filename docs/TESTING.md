# Testing Guide

## Overview

The project uses **pytest** with **pytest-django** and **factory_boy** for test fixtures. Tests live in the `tests/` directory.

## Running Tests

```bash
# Docker
make test

# Local
pytest                                          # All tests
pytest tests/test_ingestion.py                  # Single file
pytest -k "test_bulk"                           # By name pattern
pytest --cov=apps --cov-report=term-missing     # With coverage
pytest --cov=apps --cov-report=html             # HTML coverage report
pytest -x                                       # Stop on first failure
```

## Test Settings (`config.settings.test`)

| Setting | Value | Why |
|---------|-------|-----|
| `PASSWORD_HASHERS` | `MD5PasswordHasher` | 10x faster than PBKDF2 for tests |
| `CACHES` | `LocMemCache` | No Redis dependency in test runs |
| `CELERY_TASK_ALWAYS_EAGER` | `True` | Tasks execute synchronously, no worker needed |
| `DEFAULT_THROTTLE_CLASSES` | `[]` | Throttling disabled so tests aren't rate-limited |
| Database | `test_sensors` / `test:test` | Separate test database |

## Test Files

| File | Covers |
|------|--------|
| `test_auth.py` | User registration, JWT token obtain/refresh, profile |
| `test_homes.py` | Home CRUD, Space CRUD, owner isolation |
| `test_ingestion.py` | Single ingest, bulk ingest, validation (future timestamps, empty data) |
| `test_gateway.py` | Gateway key generation/rotation/revocation, gateway ingestion |
| `test_readings.py` | Reading list, filtering (from_date, to_date), latest endpoint, caching |
| `test_public.py` | Public sensor access, private sensor rejection |

## Fixtures (`tests/conftest.py`)

| Fixture | Returns | Description |
|---------|---------|-------------|
| `api_client` | `APIClient()` | Unauthenticated DRF test client |
| `user` | `User` | A fresh user (password: `testpass123`) |
| `authenticated_client` | `APIClient` | Client with `user` force-authenticated. `client.user` available. |
| `home` | `Home` | Belongs to `user` |
| `space` | `Space` | Belongs to `home` |
| `sensor` | `Sensor` | Belongs to `space`. Has `_raw_api_key` attribute. |
| `sensor_with_key` | `Sensor` | Alias for `sensor` (backward compat) |
| `home_with_gateway` | `Home` | Home with a pre-generated gateway key. Has `_raw_api_key` attribute. |
| `gateway_setup` | `dict` | Full setup: home + 2 spaces + 3 sensors. Keys: `home`, `spaces`, `sensors` |

## Factories (`tests/factories.py`)

| Factory | Model | Key Attributes |
|---------|-------|---------------|
| `UserFactory` | `User` | `username`: `user0`, `user1`, ... / `password`: `testpass123` |
| `HomeFactory` | `Home` | No gateway key by default |
| `HomeWithGatewayFactory` | `Home` | Pre-generated gateway key. `instance._raw_api_key` available. |
| `SpaceFactory` | `Space` | `is_public=False` by default |
| `SensorFactory` | `Sensor` | Pre-generated sensor key. `instance._raw_api_key` available. |
| `SensorReadingFactory` | `SensorReading` | Default data: `{"temperature": 25.6, "humidity": 48.2}` |

### Accessing Raw API Keys in Tests

Factories auto-generate keys and stash the raw key on the instance:

```python
sensor = SensorFactory()
raw_key = sensor._raw_api_key  # Use this in X-Sensor-Key header

home = HomeWithGatewayFactory()
raw_key = home._raw_api_key    # Use this in X-Gateway-Key header
```

## Writing Tests — Patterns

### Authenticated Request

```python
def test_list_homes(authenticated_client, home):
    response = authenticated_client.get('/api/v1/homes/')
    assert response.status_code == 200
    assert len(response.data['results']) == 1
```

### Sensor Ingestion

```python
def test_ingest_reading(api_client, sensor):
    response = api_client.post(
        '/api/v1/ingest/',
        data={'data': {'temperature': 22.5}},
        format='json',
        HTTP_X_SENSOR_KEY=sensor._raw_api_key,
    )
    assert response.status_code == 201
```

### Gateway Ingestion

```python
def test_gateway_ingest(api_client, gateway_setup):
    home = gateway_setup['home']
    sensors = gateway_setup['sensors']
    response = api_client.post(
        '/api/v1/ingest/gateway/',
        data={
            'readings': [
                {'sensor_id': str(sensors[0].id), 'data': {'temperature': 22.5}},
                {'sensor_id': str(sensors[1].id), 'data': {'co2': 400}},
            ]
        },
        format='json',
        HTTP_X_GATEWAY_KEY=home._raw_api_key,
    )
    assert response.status_code == 201
    assert response.data['count'] == 2
```

### Owner Isolation

```python
def test_cannot_access_others_home(api_client):
    other_user = UserFactory()
    other_home = HomeFactory(owner=other_user)

    my_user = UserFactory()
    api_client.force_authenticate(user=my_user)

    response = api_client.get(f'/api/v1/homes/{other_home.id}/')
    assert response.status_code == 404  # Not 403 — we don't leak existence
```

## Coverage Targets

| Area | Priority |
|------|----------|
| Ingestion (single, bulk, gateway) | Critical |
| Authentication (JWT, sensor key, gateway key) | Critical |
| Owner isolation / permissions | High |
| Reading queries & filtering | High |
| Public vs private access | High |
| Key rotation | Medium |
| Celery tasks | Medium |
| Edge cases (empty data, future timestamps, max bulk) | Medium |

