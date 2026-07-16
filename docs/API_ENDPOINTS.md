# API Endpoints Reference

All endpoints are prefixed with `/api/v1/`. Interactive docs available at `/api/docs/` (Swagger UI).

---

## Authentication

| Method | Endpoint | Auth | View | Description |
|--------|----------|------|------|-------------|
| `POST` | `/auth/register/` | None | `UserRegistrationView` | Register a new user |
| `POST` | `/auth/token/` | None | `TokenObtainPairView` (SimpleJWT) | Get JWT access + refresh tokens |
| `POST` | `/auth/token/refresh/` | None | `TokenRefreshView` (SimpleJWT) | Refresh an access token |
| `GET` `PATCH` | `/auth/profile/` | JWT | `UserProfileView` | View/update current user profile |

**URL file:** `apps/accounts/urls.py`

---

## Homes

| Method | Endpoint | Auth | View | Throttle |
|--------|----------|------|------|----------|
| `GET` | `/homes/` | JWT | `HomeListCreateView` | `management` |
| `POST` | `/homes/` | JWT | `HomeListCreateView` | `management` |
| `GET` `PUT` `PATCH` `DELETE` | `/homes/<uuid>/` | JWT | `HomeDetailView` | `management` |
| `POST` | `/homes/<uuid>/gateway-key/` | JWT | `HomeGatewayKeyView` | `management` |
| `DELETE` | `/homes/<uuid>/gateway-key/` | JWT | `HomeGatewayKeyView` | `management` |

**URL file:** `apps/homes/urls.py` (homes, spaces) + `apps/sensors/urls.py` (gateway-key)

### Notes
- `GET /homes/` uses `HomeListSerializer` (flat, no nested spaces)
- `GET /homes/<uuid>/` uses `HomeSerializer` (includes nested `spaces`)
- `POST /homes/` auto-sets `owner` to `request.user`

---

## Spaces

| Method | Endpoint | Auth | View | Throttle |
|--------|----------|------|------|----------|
| `GET` `POST` | `/homes/<home_uuid>/spaces/` | JWT | `SpaceListCreateView` | `management` |
| `GET` `PUT` `PATCH` `DELETE` | `/spaces/<uuid>/` | JWT | `SpaceDetailView` | `management` |

**URL file:** `apps/homes/urls.py`

### Notes
- `POST` auto-sets `home` from the URL parameter
- `is_public` field controls whether sensor data is publicly accessible

---

## Sensors

| Method | Endpoint | Auth | View | Throttle |
|--------|----------|------|------|----------|
| `GET` `POST` | `/spaces/<space_uuid>/sensors/` | JWT | `SensorListCreateView` | `management` |
| `GET` `PUT` `PATCH` `DELETE` | `/sensors/<uuid>/` | JWT | `SensorDetailView` | `management` |
| `POST` | `/sensors/<uuid>/rotate-key/` | JWT | `SensorRotateKeyView` | `management` |

**URL file:** `apps/sensors/urls.py`

### Notes
- `POST` creates a sensor and returns the raw API key **once** (never stored, never shown again)
- `POST /rotate-key/` generates a new key, invalidating the old one
- Response includes `api_key` field only on create and rotate

---

## Data Ingestion

| Method | Endpoint | Auth | View | Throttle |
|--------|----------|------|------|----------|
| `POST` | `/ingest/` | `X-Sensor-Key` | `IngestView` | `ingestion` |
| `POST` | `/ingest/bulk/` | `X-Sensor-Key` | `BulkIngestView` | `ingestion` |
| `POST` | `/ingest/gateway/` | `X-Gateway-Key` | `GatewayIngestView` | `ingestion` |

**URL file:** `apps/sensors/urls.py`

### Request Formats

**Single ingest** (`/ingest/`):
```json
{
  "data": {"temperature": 25.6, "humidity": 48.2},
  "recorded_at": "2026-07-16T10:30:00Z"  // optional
}
```

**Bulk ingest** (`/ingest/bulk/`):
```json
[
  {"data": {"temperature": 25.6}, "recorded_at": "2026-07-16T10:30:00Z"},
  {"data": {"temperature": 25.8}, "recorded_at": "2026-07-16T10:31:00Z"}
]
```

**Gateway ingest** (`/ingest/gateway/`):
```json
{
  "readings": [
    {"sensor_id": "<uuid>", "data": {"temperature": 25.6}},
    {"sensor_id": "<uuid>", "data": {"co2": 412}, "recorded_at": "2026-07-16T10:31:00Z"}
  ]
}
```

### Validation Rules
- `data` must be a non-empty JSON object
- `recorded_at` is optional (defaults to server time)
- `recorded_at` cannot be in the future
- `recorded_at` cannot be more than 30 days in the past
- Max 1000 readings per bulk/gateway request
- Gateway validates all `sensor_id`s belong to the home and are active

---

## Readings

| Method | Endpoint | Auth | View | Throttle |
|--------|----------|------|------|----------|
| `GET` | `/sensors/<uuid>/readings/` | JWT | `SensorReadingListView` | `readings` |
| `GET` | `/sensors/<uuid>/readings/latest/` | JWT | `SensorReadingLatestView` | `readings` |

**URL file:** `apps/sensors/urls.py`

### Query Parameters (readings list)

| Param | Type | Description |
|-------|------|-------------|
| `from_date` | ISO 8601 datetime | Readings at or after this time |
| `to_date` | ISO 8601 datetime | Readings at or before this time |
| `ordering` | string | `recorded_at` or `-recorded_at` (default: `-recorded_at`) |
| `limit` | integer | Page size (default: 50, max: 1000) |
| `page` | integer | Page number |

### Notes
- `/latest/` is served from Redis cache (zero DB queries on cache hit)
- Readings are filtered by `SensorReadingFilter` (django-filter)
- Pagination uses `StandardPagination` (page number style)

---

## Public Endpoints

| Method | Endpoint | Auth | View |
|--------|----------|------|------|
| `GET` | `/public/sensors/<uuid>/readings/` | None | `PublicSensorReadingListView` |
| `GET` | `/public/sensors/<uuid>/readings/latest/` | None | `PublicSensorReadingLatestView` |

**URL file:** `apps/sensors/urls.py`

### Notes
- Only accessible if the sensor's space has `is_public=True`
- Same query parameters as authenticated readings
- Permission check: `IsSensorPublic`

---

## System

| Method | Endpoint | Auth | View |
|--------|----------|------|------|
| `GET` | `/health/` | None | `HealthCheckView` |

**URL file:** `apps/common/urls.py`

Returns `200` with `{"status": "healthy"}` or `503` with `{"status": "unhealthy"}`. Checks both database and Redis connectivity.

---

## URL Configuration

Root URL conf is `config/urls.py`:

```python
path('api/v1/auth/', include('apps.accounts.urls'))    # Auth endpoints
path('api/v1/',      include('apps.homes.urls'))        # Home + Space endpoints
path('api/v1/',      include('apps.sensors.urls'))      # Sensor, ingest, reading endpoints
path('api/v1/health/', include('apps.common.urls'))     # Health check
path('api/schema/',  SpectacularAPIView)                # OpenAPI schema
path('api/docs/',    SpectacularSwaggerView)             # Swagger UI
path('admin/',       admin.site.urls)                    # Django admin
```

