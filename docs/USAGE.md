# Getting Started — User Journey

This guide walks through the complete flow: from registration to collecting and querying sensor data.

## Base URL

```
https://your-domain.com/api/v1
```

Interactive API documentation (Swagger UI) is available at:

```
https://your-domain.com/api/docs/
```

---

## Step 1: Register an Account

```bash
curl -X POST https://your-domain.com/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "email": "john@example.com",
    "password": "MySecurePass123",
    "password_confirm": "MySecurePass123"
  }'
```

**Response (201 Created):**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "username": "john",
  "email": "john@example.com"
}
```

---

## Step 2: Obtain a JWT Token

```bash
curl -X POST https://your-domain.com/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "password": "MySecurePass123"
  }'
```

**Response (200 OK):**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOi..."
}
```

For convenience, export the access token:

```bash
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOi..."
```

Access tokens expire after **15 minutes**. Use the refresh endpoint to get a new one:

```bash
curl -X POST https://your-domain.com/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOi..."}'
```

Refresh tokens are valid for **7 days** and rotate on each use (the old one is blacklisted).

---

## Step 3: Create a Home

A home is the top-level container that groups all your spaces and sensors.

```bash
curl -X POST https://your-domain.com/api/v1/homes/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "My Apartment",
    "location": "Athens, Greece"
  }'
```

**Response (201 Created):**

```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "name": "My Apartment",
  "location": "Athens, Greece",
  "spaces": [],
  "created_at": "2026-07-16T10:00:00Z",
  "updated_at": "2026-07-16T10:00:00Z"
}
```

> 📌 Save the home `id` — you'll need it to create spaces.

---

## Step 4: Create Spaces (Rooms)

Spaces represent physical areas within a home (rooms, balconies, etc.).

```bash
curl -X POST https://your-domain.com/api/v1/homes/b2c3d4e5-f6a7-8901-bcde-f12345678901/spaces/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Living Room",
    "is_public": false
  }'
```

**Response (201 Created):**

```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "home": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "name": "Living Room",
  "is_public": false,
  "created_at": "2026-07-16T10:01:00Z",
  "updated_at": "2026-07-16T10:01:00Z"
}
```

You can create a **public** space whose sensor data anyone can read without authentication (e.g., for a weather station):

```bash
curl -X POST https://your-domain.com/api/v1/homes/b2c3d4e5-f6a7-8901-bcde-f12345678901/spaces/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Balcony", "is_public": true}'
```

> 📌 Save each space `id` — you'll need it to register sensors.

---

## Step 5: Register Sensors

Add sensors to a space. Each sensor gets a unique API key for direct data ingestion.

```bash
curl -X POST https://your-domain.com/api/v1/spaces/c3d4e5f6-a7b8-9012-cdef-123456789012/sensors/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Living Room Temp/Humidity",
    "sensor_type": "DHT22"
  }'
```

**Response (201 Created):**

```json
{
  "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "name": "Living Room Temp/Humidity",
  "sensor_type": "DHT22",
  "api_key": "xK9mP2qR7vL4nW8jT5cY1bA3hF6gD0eU_ZsXwQrMtNpJkBiOlCa",
  "is_active": true,
  "created_at": "2026-07-16T10:02:00Z"
}
```

> ⚠️ **Save the `api_key`!** It is only shown in full at creation time. This key is used by the sensor (or gateway) to send data.

> 📌 Save the sensor `id` — you'll need it if using the gateway ingestion method.

---

## Step 6: Send Sensor Data

There are **two ingestion modes** depending on your hardware setup.

### Option A: Direct Sensor Ingestion (`X-Sensor-Key`)

Each sensor authenticates with its own key. Best for **WiFi-enabled sensors** (ESP32, ESP8266) that connect directly to the internet.

#### Single reading

```bash
curl -X POST https://your-domain.com/api/v1/ingest/ \
  -H "Content-Type: application/json" \
  -H "X-Sensor-Key: xK9mP2qR7vL4nW8jT5cY1bA3hF6gD0eU_ZsXwQrMtNpJkBiOlCa" \
  -d '{
    "data": {
      "temperature": 25.6,
      "humidity": 48.2,
      "battery_voltage": 3.2
    }
  }'
```

**Response (201 Created):**

```json
{
  "id": 1,
  "recorded_at": "2026-07-16T10:05:00Z"
}
```

#### Bulk upload (buffered / offline readings)

```bash
curl -X POST https://your-domain.com/api/v1/ingest/bulk/ \
  -H "Content-Type: application/json" \
  -H "X-Sensor-Key: xK9mP2qR7vL4nW8jT5cY1bA3hF6gD0eU_ZsXwQrMtNpJkBiOlCa" \
  -d '[
    {"data": {"temperature": 25.6, "humidity": 48.2}, "recorded_at": "2026-07-16T10:00:00Z"},
    {"data": {"temperature": 25.8, "humidity": 47.9}, "recorded_at": "2026-07-16T10:01:00Z"}
  ]'
```

**Response (201 Created):**

```json
{
  "count": 2
}
```

---

### Option B: Gateway Ingestion (`X-Gateway-Key`)

A central gateway device (e.g., Raspberry Pi, Home Assistant) collects data from **all sensors in a home** via Zigbee, BLE, or wired connections, then sends everything in **one request** using a single home-level key.

#### B.1 — Generate a gateway key for your home

```bash
curl -X POST https://your-domain.com/api/v1/homes/b2c3d4e5-f6a7-8901-bcde-f12345678901/gateway-key/ \
  -H "Authorization: Bearer $TOKEN"
```

**Response (200 OK):**

```json
{
  "api_key": "gw_R7vL4nW8jT5cY1bA3hF6gD0eU_ZsXwQrMtNpJkBiOlCaAbCdEf"
}
```

> ⚠️ Save this key and configure it on your gateway device.

#### B.2 — Send data for multiple sensors in one request

Each reading includes a `sensor_id` to identify which sensor the data belongs to:

```bash
curl -X POST https://your-domain.com/api/v1/ingest/gateway/ \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Key: gw_R7vL4nW8jT5cY1bA3hF6gD0eU_ZsXwQrMtNpJkBiOlCaAbCdEf" \
  -d '{
    "readings": [
      {
        "sensor_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
        "data": {"temperature": 25.6, "humidity": 48.2}
      },
      {
        "sensor_id": "e5f6a7b8-c901-2345-efab-345678901234",
        "data": {"co2": 412, "tvoc": 15, "pressure": 1013.25}
      },
      {
        "sensor_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
        "data": {"temperature": 25.8, "humidity": 47.9},
        "recorded_at": "2026-07-16T10:01:00Z"
      }
    ]
  }'
```

**Response (201 Created):**

```json
{
  "count": 3,
  "sensors": 2
}
```

The server validates that every `sensor_id` belongs to this home and is active. If any are invalid, the entire request is rejected with the list of bad IDs.

---

### Choosing between Option A and Option B

| Scenario | Auth Header | Endpoint |
|----------|-------------|----------|
| WiFi sensor sends its own data directly | `X-Sensor-Key` | `POST /api/v1/ingest/` or `/ingest/bulk/` |
| Central gateway collects from many sensors | `X-Gateway-Key` | `POST /api/v1/ingest/gateway/` |

Both methods support the optional `recorded_at` field (defaults to server time). Validated: cannot be in the future, maximum 30 days backfill. Maximum **1000 readings** per bulk or gateway request.

---

## Step 7: Query Your Data

### Latest reading (served from Redis cache — zero DB queries)

```bash
curl https://your-domain.com/api/v1/sensors/d4e5f6a7-b8c9-0123-defa-234567890123/readings/latest/ \
  -H "Authorization: Bearer $TOKEN"
```

**Response (200 OK):**

```json
{
  "id": 1,
  "sensor": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "data": {
    "temperature": 25.6,
    "humidity": 48.2,
    "battery_voltage": 3.2
  },
  "recorded_at": "2026-07-16T10:05:00Z"
}
```

### Historical readings (with filtering and pagination)

```bash
curl "https://your-domain.com/api/v1/sensors/d4e5f6a7-b8c9-0123-defa-234567890123/readings/?from_date=2026-07-16T00:00:00Z&to_date=2026-07-16T23:59:59Z&limit=100" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (200 OK):**

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 3,
      "sensor": "d4e5f6a7-b8c9-0123-defa-234567890123",
      "data": {"temperature": 26.0, "humidity": 47.5},
      "recorded_at": "2026-07-16T10:02:00Z"
    },
    {
      "id": 2,
      "sensor": "d4e5f6a7-b8c9-0123-defa-234567890123",
      "data": {"temperature": 25.8, "humidity": 47.9},
      "recorded_at": "2026-07-16T10:01:00Z"
    },
    {
      "id": 1,
      "sensor": "d4e5f6a7-b8c9-0123-defa-234567890123",
      "data": {"temperature": 25.6, "humidity": 48.2},
      "recorded_at": "2026-07-16T10:00:00Z"
    }
  ]
}
```

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `from_date` | ISO 8601 datetime — return readings recorded at or after this time |
| `to_date` | ISO 8601 datetime — return readings recorded at or before this time |
| `ordering` | Field to sort by (`recorded_at` or `-recorded_at`). Default: `-recorded_at` |
| `limit` | Page size (max 1000, default 50) |
| `page` | Page number for pagination |

---

## Public Access (No Authentication Required)

If a space is marked `is_public: true`, anyone can query its sensors' readings without a token:

```bash
# Latest reading
curl https://your-domain.com/api/v1/public/sensors/d4e5f6a7-b8c9-0123-defa-234567890123/readings/latest/

# Historical readings (same query parameters as above)
curl "https://your-domain.com/api/v1/public/sensors/d4e5f6a7-b8c9-0123-defa-234567890123/readings/?from_date=2026-07-16T00:00:00Z&limit=50"
```

---

## Key Management

### Rotate a sensor key

If a sensor key is compromised, generate a new one without re-registering:

```bash
curl -X POST https://your-domain.com/api/v1/sensors/d4e5f6a7-b8c9-0123-defa-234567890123/rotate-key/ \
  -H "Authorization: Bearer $TOKEN"
```

**Response (200 OK):**

```json
{
  "api_key": "newKeyHere_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890abcdef"
}
```

> Remember to update the key on your IoT device.

### Rotate a gateway key

```bash
curl -X POST https://your-domain.com/api/v1/homes/b2c3d4e5-f6a7-8901-bcde-f12345678901/gateway-key/ \
  -H "Authorization: Bearer $TOKEN"
```

Calling this endpoint again generates a new key and invalidates the old one.

### Revoke a gateway key

Removes the key entirely — the gateway will no longer be able to authenticate:

```bash
curl -X DELETE https://your-domain.com/api/v1/homes/b2c3d4e5-f6a7-8901-bcde-f12345678901/gateway-key/ \
  -H "Authorization: Bearer $TOKEN"
```

**Response:** `204 No Content`

---

## Other Management Endpoints

### User profile

```bash
# View profile
curl https://your-domain.com/api/v1/auth/profile/ \
  -H "Authorization: Bearer $TOKEN"

# Update profile
curl -X PATCH https://your-domain.com/api/v1/auth/profile/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"first_name": "John", "last_name": "Doe"}'
```

### List all your homes

```bash
curl https://your-domain.com/api/v1/homes/ \
  -H "Authorization: Bearer $TOKEN"
```

### View a home with all its spaces

```bash
curl https://your-domain.com/api/v1/homes/b2c3d4e5-f6a7-8901-bcde-f12345678901/ \
  -H "Authorization: Bearer $TOKEN"
```

### Update / delete a home

```bash
# Update
curl -X PATCH https://your-domain.com/api/v1/homes/b2c3d4e5-f6a7-8901-bcde-f12345678901/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Beach House"}'

# Delete (also deletes all spaces, sensors, and readings)
curl -X DELETE https://your-domain.com/api/v1/homes/b2c3d4e5-f6a7-8901-bcde-f12345678901/ \
  -H "Authorization: Bearer $TOKEN"
```

### View / update / delete a space

```bash
curl https://your-domain.com/api/v1/spaces/c3d4e5f6-a7b8-9012-cdef-123456789012/ \
  -H "Authorization: Bearer $TOKEN"

curl -X PATCH https://your-domain.com/api/v1/spaces/c3d4e5f6-a7b8-9012-cdef-123456789012/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"is_public": true}'

curl -X DELETE https://your-domain.com/api/v1/spaces/c3d4e5f6-a7b8-9012-cdef-123456789012/ \
  -H "Authorization: Bearer $TOKEN"
```

### List sensors in a space

```bash
curl https://your-domain.com/api/v1/spaces/c3d4e5f6-a7b8-9012-cdef-123456789012/sensors/ \
  -H "Authorization: Bearer $TOKEN"
```

### View / update / delete a sensor

```bash
curl https://your-domain.com/api/v1/sensors/d4e5f6a7-b8c9-0123-defa-234567890123/ \
  -H "Authorization: Bearer $TOKEN"

curl -X PATCH https://your-domain.com/api/v1/sensors/d4e5f6a7-b8c9-0123-defa-234567890123/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"is_active": false}'

curl -X DELETE https://your-domain.com/api/v1/sensors/d4e5f6a7-b8c9-0123-defa-234567890123/ \
  -H "Authorization: Bearer $TOKEN"
```

### Health check

```bash
curl https://your-domain.com/api/v1/health/
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "cache": "ok"
  }
}
```

---

## Complete API Reference

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register/` | None | Register a new account |
| `POST` | `/auth/token/` | None | Obtain JWT token pair |
| `POST` | `/auth/token/refresh/` | None | Refresh an access token |
| `GET` `PATCH` | `/auth/profile/` | JWT | View or update your profile |

### Homes

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` `POST` | `/homes/` | JWT | List your homes / create a new home |
| `GET` `PUT` `PATCH` `DELETE` | `/homes/{id}/` | JWT | View, update, or delete a home |
| `POST` `DELETE` | `/homes/{id}/gateway-key/` | JWT | Generate/rotate or revoke a gateway key |

### Spaces

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` `POST` | `/homes/{id}/spaces/` | JWT | List spaces in a home / create a new space |
| `GET` `PUT` `PATCH` `DELETE` | `/spaces/{id}/` | JWT | View, update, or delete a space |

### Sensors

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` `POST` | `/spaces/{id}/sensors/` | JWT | List sensors in a space / register a new sensor |
| `GET` `PUT` `PATCH` `DELETE` | `/sensors/{id}/` | JWT | View, update, or delete a sensor |
| `POST` | `/sensors/{id}/rotate-key/` | JWT | Rotate a sensor's API key |

### Data Ingestion

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/ingest/` | `X-Sensor-Key` | Ingest a single reading from one sensor |
| `POST` | `/ingest/bulk/` | `X-Sensor-Key` | Ingest multiple readings from one sensor |
| `POST` | `/ingest/gateway/` | `X-Gateway-Key` | Ingest readings from multiple sensors via a gateway |

### Readings

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/sensors/{id}/readings/` | JWT | List readings (filterable, paginated) |
| `GET` | `/sensors/{id}/readings/latest/` | JWT | Get the latest reading (cached) |
| `GET` | `/public/sensors/{id}/readings/` | None | List readings for a public sensor |
| `GET` | `/public/sensors/{id}/readings/latest/` | None | Latest reading for a public sensor |

### System

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health/` | None | Database and cache health check |

---

## Authentication Summary

```
┌─────────────────────┬───────────────────────────┬────────────────────────────────────────┐
│ Who                 │ Auth Header               │ Use Case                               │
├─────────────────────┼───────────────────────────┼────────────────────────────────────────┤
│ Human / Dashboard   │ Authorization: Bearer JWT │ Account, home, space, sensor mgmt      │
│                     │                           │ + querying readings                    │
├─────────────────────┼───────────────────────────┼────────────────────────────────────────┤
│ Single IoT sensor   │ X-Sensor-Key: <key>       │ POST /ingest/ or /ingest/bulk/         │
│ (ESP32, etc.)       │                           │ One key per sensor                     │
├─────────────────────┼───────────────────────────┼────────────────────────────────────────┤
│ Central gateway     │ X-Gateway-Key: <key>      │ POST /ingest/gateway/                  │
│ (RPi, HA, etc.)     │                           │ One key per home, many sensors         │
└─────────────────────┴───────────────────────────┴────────────────────────────────────────┘
```
