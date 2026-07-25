"""
Home Sensor Platform — Raspberry Pi Client
==========================================

Sends sensor data to the Home Sensor Platform API.
Supports both per-sensor keys (X-Sensor-Key) and gateway keys (X-Gateway-Key).

Usage:
    # Gateway mode (recommended): one key sends data for all sensors in a home
    python3 send_data.py

    # Or called with arguments from bluetooth listener:
    python3 send_data.py <mac> <name> <temp> <humidity> <battery> <battery_lvl> <signal>

Requirements:
    pip3 install requests

Configuration:
    Copy config.example.json to config.json and fill in your values.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

# --- Configuration ---

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')
UNSENT_FILE = os.path.join(SCRIPT_DIR, 'unsent_data.json')
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds, doubles each retry
UNSENT_MAX_AGE_HOURS = 72  # discard unsent data older than this


def load_config():
    """Load configuration from config.json."""
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: {CONFIG_FILE} not found. Copy config.example.json and fill in your values.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def log(message, filename='client.log'):
    """Append a timestamped log entry."""
    os.makedirs(LOG_DIR, exist_ok=True)
    filepath = os.path.join(LOG_DIR, filename)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(filepath, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


# --- HTTP Client ---

class SensorClient:
    """Client for the Home Sensor Platform API."""

    def __init__(self, config):
        self.base_url = config['api_url'].rstrip('/')
        self.gateway_key = config.get('gateway_key', '')
        self.sensors = config.get('sensors', {})
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'rpi-sensor-client/2.0',
        })

        if self.gateway_key:
            self.session.headers['X-Gateway-Key'] = self.gateway_key

    def _request(self, method, endpoint, data=None):
        """Make an HTTP request with retries."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if method == 'POST':
                    resp = self.session.post(url, json=data, timeout=30)
                else:
                    resp = self.session.get(url, timeout=30)

                if resp.status_code in (200, 201):
                    log(f"OK {method} {endpoint} → {resp.status_code}")
                    return resp

                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    log(f"FAIL {method} {endpoint} → {resp.status_code}: {resp.text[:200]}", 'errors.log')
                    return resp

                # Retryable (5xx, 429)
                log(f"RETRY {attempt}/{MAX_RETRIES} {endpoint} → {resp.status_code}", 'errors.log')

            except requests.exceptions.RequestException as e:
                log(f"RETRY {attempt}/{MAX_RETRIES} {endpoint} → {e}", 'errors.log')

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * (2 ** (attempt - 1)))

        return None

    # --- Gateway ingestion (recommended) ---

    def send_gateway(self, readings):
        """
        Send multiple sensor readings via gateway endpoint.

        Args:
            readings: list of dicts with keys:
                - sensor_id: UUID of the sensor
                - data: dict of measurements (e.g. {"temperature": 25.6})
                - recorded_at: (optional) ISO timestamp

        Returns:
            True on success, False on failure (data buffered).
        """
        payload = {'readings': readings}
        resp = self._request('POST', '/api/v1/ingest/gateway/', data=payload)

        if resp and resp.status_code in (200, 201):
            log(f"Sent {len(readings)} readings via gateway")
            return True

        # Buffer for retry
        self._save_unsent(readings)
        log(f"BUFFERED {len(readings)} readings for retry", 'errors.log')
        return False

    # --- Per-sensor ingestion (alternative) ---

    def send_single(self, sensor_key, data, recorded_at=None):
        """
        Send a single reading using per-sensor key auth.

        Args:
            sensor_key: The X-Sensor-Key for this sensor.
            data: dict of measurements.
            recorded_at: (optional) ISO timestamp.
        """
        headers = {'X-Sensor-Key': sensor_key}
        payload = {'data': data}
        if recorded_at:
            payload['recorded_at'] = recorded_at

        # Temporarily override session headers
        old_headers = dict(self.session.headers)
        self.session.headers.update(headers)
        self.session.headers.pop('X-Gateway-Key', None)

        resp = self._request('POST', '/api/v1/ingest/', data=payload)

        self.session.headers = old_headers
        return resp and resp.status_code in (200, 201)

    # --- Offline buffer ---

    def _save_unsent(self, readings):
        """Save failed readings to disk for later retry."""
        existing = self._load_unsent()
        for r in readings:
            r['_buffered_at'] = datetime.now(timezone.utc).isoformat()
        existing.extend(readings)
        try:
            with open(UNSENT_FILE, 'w') as f:
                json.dump(existing, f)
        except OSError as e:
            log(f"Cannot save unsent buffer: {e}", 'errors.log')

    def _load_unsent(self):
        """Load buffered readings from disk."""
        if not os.path.exists(UNSENT_FILE):
            return []
        try:
            with open(UNSENT_FILE) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _clear_unsent(self):
        """Remove the buffer file."""
        try:
            os.remove(UNSENT_FILE)
        except OSError:
            pass

    def flush_unsent(self):
        """Retry sending any buffered readings."""
        unsent = self._load_unsent()
        if not unsent:
            return

        # Drop readings older than MAX_AGE
        cutoff = time.time() - (UNSENT_MAX_AGE_HOURS * 3600)
        fresh = []
        for r in unsent:
            buffered = r.pop('_buffered_at', None)
            if buffered:
                try:
                    ts = datetime.fromisoformat(buffered).timestamp()
                    if ts < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass
            fresh.append(r)

        if not fresh:
            self._clear_unsent()
            return

        payload = {'readings': fresh}
        resp = self._request('POST', '/api/v1/ingest/gateway/', data=payload)

        if resp and resp.status_code in (200, 201):
            self._clear_unsent()
            log(f"Flushed {len(fresh)} buffered readings")
        else:
            # Re-save (without expired ones)
            try:
                with open(UNSENT_FILE, 'w') as f:
                    json.dump(fresh, f)
            except OSError:
                pass


# --- Main entry point ---

def main():
    config = load_config()
    client = SensorClient(config)

    # Flush any previously unsent data
    client.flush_unsent()

    # If called with command-line arguments (from bluetooth listener)
    if len(sys.argv) >= 8:
        # Format: send_data.py <mac> <name> <temp> <humidity> <battery> <battery_lvl> <signal>
        mac = sys.argv[1]
        name = sys.argv[2]
        temp = float(sys.argv[3])
        humidity = float(sys.argv[4])
        battery = float(sys.argv[5])
        battery_lvl = float(sys.argv[6])
        signal_strength = float(sys.argv[7])

        # Look up sensor_id by MAC address or name
        sensor_id = config['sensors'].get(mac) or config['sensors'].get(name)
        if not sensor_id:
            log(f"Unknown sensor: {mac} / {name}", 'errors.log')
            sys.exit(1)

        readings = [{
            'sensor_id': sensor_id,
            'data': {
                'temperature': temp,
                'humidity': humidity,
                'battery_voltage': battery,
                'battery_percentage': battery_lvl,
                'signal': signal_strength,
            }
        }]

        client.send_gateway(readings)

    else:
        # Manual/cron mode: collect from all configured sensors
        # Customize this section for your sensor setup
        print("No arguments provided. Use with bluetooth listener or customize for your sensors.")
        print("Example: python3 send_data.py AA:BB:CC:DD:EE:FF MySensor 22.5 45.0 3.1 85 -60")


if __name__ == '__main__':
    main()

