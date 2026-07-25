# Home Sensor Platform — Raspberry Pi Client

Lightweight Python client for sending sensor data to the Home Sensor Platform API.

## Quick Setup

```bash
# On your Raspberry Pi
pip3 install requests

# Copy and configure
cp config.example.json config.json
nano config.json  # Fill in your gateway key and sensor UUIDs
```

## Configuration

Get your **gateway key** from the API:
```bash
# First, get a JWT token
TOKEN=$(curl -s -X POST https://logs.tsaklidis.gr/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"you","password":"pass"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# Generate a gateway key for your home
curl -X POST https://logs.tsaklidis.gr/api/v1/homes/YOUR_HOME_UUID/gateway-key/ \
  -H "Authorization: Bearer $TOKEN"
```

The response contains your `api_key` — put it in `config.json` as `gateway_key`.

## Usage

### With Bluetooth listener (like the old system)
```bash
# Called by your bluetooth scanner when a sensor broadcasts:
python3 send_data.py "A4:C1:38:XX:XX:XX" "LYWSD03MMC" 22.5 48.0 3.1 85 -55
```

Arguments: `<mac> <name> <temperature> <humidity> <battery_v> <battery_%> <signal>`

### From a cron job or custom script
```python
from send_data import SensorClient, load_config

config = load_config()
client = SensorClient(config)

# Send readings for multiple sensors at once
readings = [
    {
        "sensor_id": "uuid-of-temp-sensor",
        "data": {"temperature": 22.5, "humidity": 48.2}
    },
    {
        "sensor_id": "uuid-of-outdoor-sensor", 
        "data": {"temperature": 15.0, "pressure": 1013.25}
    }
]

client.send_gateway(readings)
```

## Features

- **Offline buffering**: Failed sends are saved to `unsent_data.json` and retried next run
- **Auto-retry**: 3 attempts with exponential backoff
- **Logging**: All activity logged to `logs/` directory
- **Gateway mode**: One API key sends data for all sensors in a home
- **Per-sensor mode**: Alternative if you want per-sensor keys

## Migration from old system

| Old (LogingAPI) | New (Home Sensor Platform) |
|-----------------|---------------------------|
| Token auth (username/password) | Gateway key (`X-Gateway-Key` header) |
| One value per sensor per request | Multiple values in JSON payload |
| `credentials.py` with UUIDs | `config.json` with sensor mapping |
| `api.py` + `send_data.py` | Single `send_data.py` |

## Files

```
client/
├── send_data.py          # Main script
├── config.example.json   # Configuration template
├── config.json           # Your config (gitignored)
├── unsent_data.json      # Offline buffer (auto-created)
└── logs/                 # Log files (auto-created)
    ├── client.log
    └── errors.log
```

