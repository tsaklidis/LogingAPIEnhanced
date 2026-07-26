# Grafana Dashboards for Home Sensors

Beautiful dashboards for monitoring home IoT sensors stored in PostgreSQL.

## Dashboard: 🏠 Home Sensors

### Panels

| Section | Visualization | Description |
|---------|--------------|-------------|
| 🌡️ Temperature | Time series + Stat cards | All 4 rooms overlaid with color-coded lines, plus current values with sparklines |
| 💧 Humidity | Time series + Gauges | Humidity trends with gauge indicators per room |
| 🔋 Battery | Two time series | Battery percentage and voltage side by side |
| 📶 Signal | Time series + Status cards | RSSI history with quality labels (Excellent/Good/Fair/Weak/Poor) |
| 📊 System | Stats + Table | Total readings (24h), active sensors, last reading age, last-seen table |

### Rooms / Sensors

| Room | MAC Address |
|------|-------------|
| Σαλόνι (Living Room) | A4:C1:38:AB:CA:21 |
| Αποθήκη (Storage) | A4:C1:38:89:6B:CA |
| Office | A4:C1:38:40:73:5F |
| Bedroom | A4:C1:38:07:C7:8F |

## Deployment

### Option A: Quick Deploy via Script

```bash
# Set Grafana credentials (defaults: admin/admin)
export GRAFANA_USER=admin
export GRAFANA_PASS=admin
export GRAFANA_URL=http://localhost:3000

# Run deploy script
chmod +x grafana/deploy-dashboard.sh
./grafana/deploy-dashboard.sh
```

### Option B: Manual Import

1. Open Grafana at `http://<server-ip>:3000`
2. Go to **Dashboards → Import**
3. Upload `grafana/dashboards/home-sensors.json`
4. Select your PostgreSQL datasource when prompted

### Option C: Docker Provisioning (Recommended for fresh installs)

If you're setting up Grafana from scratch, mount the provisioning files:

```yaml
# In your docker-compose.yml for Grafana:
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## PostgreSQL Datasource Configuration

The dashboard expects a PostgreSQL datasource with UID `sensor-platform-postgres` pointing to the `sensor_platform` database.

| Setting | Value |
|---------|-------|
| Host | `postgres:5432` (Docker network) or your DB host |
| Database | `sensor_platform` |
| User | `postgres` |
| SSL Mode | disable |

## Query Notes

The dashboard queries use `COALESCE` to handle both data formats:
- `data->>'temperature'` — when the full payload is stored per sensor
- `data->>'value'` — when single values are stored per measurement-type sensor

If your data uses a different JSON key structure, update the SQL queries in the dashboard panels.

