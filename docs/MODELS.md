# Data Models Reference

## Entity Relationship Diagram

```
┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌────────────────┐
│   User   │1────*│   Home   │1────*│  Space   │1────*│  Sensor  │1────*│ SensorReading  │
│ (UUID PK)│       │ (UUID PK)│       │ (UUID PK)│       │ (UUID PK)│       │ (BigAuto PK)   │
└──────────┘       └──────────┘       └──────────┘       └──────────┘       └────────────────┘
```

**Ownership chain:** `User → Home → Space → Sensor → SensorReading`

All access control follows this chain — a user can only access resources they own.

---

## User (`apps.accounts.models.User`)

Extends Django's `AbstractUser` with a UUID primary key.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `UUIDField` (PK) | Auto-generated, not editable |
| _inherited_ | — | `username`, `email`, `password`, `first_name`, `last_name`, etc. |

**Table:** `users`

---

## Home (`apps.homes.models.Home`)

Top-level container representing a physical home/building.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `UUIDField` (PK) | Auto-generated |
| `owner` | `FK → User` | CASCADE delete. Indexed. |
| `name` | `CharField(128)` | Required |
| `location` | `CharField(255)` | Optional (blank allowed) |
| `key_prefix` | `CharField(16)` | Gateway API key prefix for fast lookup. Indexed. Blank = no gateway key. |
| `key_hash` | `CharField(64)` | SHA-256 hash of full gateway API key. Blank = no gateway key. |
| `created_at` | `DateTimeField` | Auto-set on creation |
| `updated_at` | `DateTimeField` | Auto-set on every save |

**Table:** `homes`
**Indexes:** `owner`
**Related names:** `user.homes`
**Property:** `has_gateway_key` → `bool(self.key_hash)`

---

## Space (`apps.homes.models.Space`)

A physical area within a home (room, balcony, garage, etc.).

| Field | Type | Notes |
|-------|------|-------|
| `id` | `UUIDField` (PK) | Auto-generated |
| `home` | `FK → Home` | CASCADE delete |
| `name` | `CharField(128)` | e.g., "Living Room", "Balcony" |
| `is_public` | `BooleanField` | Default: `False`. When `True`, sensor readings are publicly accessible without auth. |
| `created_at` | `DateTimeField` | Auto-set |
| `updated_at` | `DateTimeField` | Auto-set |

**Table:** `spaces`
**Related names:** `home.spaces`

---

## Sensor (`apps.sensors.models.Sensor`)

An IoT device registered to a space.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `UUIDField` (PK) | Auto-generated |
| `space` | `FK → Space` | CASCADE delete |
| `name` | `CharField(128)` | Human-readable name |
| `sensor_type` | `CharField(64)` | Hardware type: `"DHT22"`, `"BME280"`, `"BMP180"`, etc. |
| `key_prefix` | `CharField(16)` | Sensor API key prefix. Indexed. |
| `key_hash` | `CharField(64)` | SHA-256 hash of full sensor API key. |
| `is_active` | `BooleanField` | Default: `True`. Inactive sensors can't authenticate. |
| `created_at` | `DateTimeField` | Auto-set |
| `updated_at` | `DateTimeField` | Auto-set |

**Table:** `sensors`
**Related names:** `space.sensors`

---

## SensorReading (`apps.sensors.models.SensorReading`)

A single data packet from a sensor. This is the high-volume table.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `BigAutoField` (PK) | Supports billions of rows |
| `sensor` | `FK → Sensor` | CASCADE delete |
| `data` | `JSONField` | Flexible payload. Example: `{"temperature": 25.6, "humidity": 48.2}` |
| `recorded_at` | `DateTimeField` | When the reading was taken. Defaults to `timezone.now()`. Validated: not future, max 30 days back. |

**Table:** `sensor_readings`
**Ordering:** `-recorded_at` (newest first)
**Indexes:** `(sensor, -recorded_at)` — composite index for the most common query pattern
**Related names:** `sensor.readings`

---

## API Key Storage Pattern

Both `Sensor` and `Home` use the same key pattern via `apps.common.apikey`:

```
key_prefix: "aB3xK9mP"          ← stored, indexed, used for fast DB lookup
key_hash:   "e3b0c44298fc..."    ← stored, SHA-256 of full key
raw key:    "aB3xK9mP.Lq7..."   ← shown once at creation, NEVER stored
```

- **Lookup:** `WHERE key_prefix = ?` (indexed, O(1))
- **Verification:** `hmac.compare_digest(sha256(raw_key), stored_hash)` (constant-time)

---

## Serializers

| Serializer | Model | Used By | Notes |
|-----------|-------|---------|-------|
| `UserSerializer` | User | Profile view | Read: id, username, email, names |
| `UserRegistrationSerializer` | User | Registration | Write: username, email, password, password_confirm |
| `HomeSerializer` | Home | Detail/Create | Includes nested `spaces` |
| `HomeListSerializer` | Home | List view | Flat, no nested spaces |
| `SpaceSerializer` | Space | CRUD | `home` is read-only (set in view) |
| `SensorSerializer` | Sensor | List/Detail | Includes `space` FK |
| `SensorCreateSerializer` | Sensor | Create | Excludes `space` (set in view). Response includes `api_key` (added manually). |
| `SensorReadingSerializer` | SensorReading | Reading views | Fields: id, data, recorded_at |
| `IngestSerializer` | — (plain) | Single ingest | Fields: data (JSONField), recorded_at (optional) |
| `BulkIngestSerializer` | — (ListSerializer) | Bulk ingest | List of `IngestSerializer`, max 1000 items |
| `GatewayIngestItemSerializer` | — (plain) | Gateway ingest item | Fields: sensor_id, data, recorded_at |
| `GatewayIngestSerializer` | — (plain) | Gateway ingest | Wraps list of `GatewayIngestItemSerializer` under `readings` key |

