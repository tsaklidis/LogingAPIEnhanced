#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# Deploy Grafana dashboard to dulano@creations (port 9999)
#
# Prerequisites:
#   - Grafana running in Docker on the remote server
#   - PostgreSQL datasource configured in Grafana
#
# Usage:
#   ./grafana/deploy-dashboard.sh
#
# The script will:
#   1. Copy the dashboard JSON to the remote server
#   2. Import it via Grafana HTTP API
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_FILE="${1:-${SCRIPT_DIR}/dashboards/home-sensors.json}"

# Remote server
SSH_HOST="dulano@creations"
SSH_PORT="9999"
SSH_CMD="ssh -p ${SSH_PORT} ${SSH_HOST}"

# Grafana settings (adjust if different)
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-admin}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🏠 Deploying Home Sensors Dashboard to Grafana"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- Step 1: Check if datasource exists, if not create it ---
echo ""
echo "📡 Step 1: Checking PostgreSQL datasource..."

# Build the import payload (wrap dashboard JSON for the API)
IMPORT_PAYLOAD=$(python3 -c "
import json, sys

with open('${DASHBOARD_FILE}') as f:
    dashboard = json.load(f)

# Remove __inputs (used only for import UI)
inputs = dashboard.pop('__inputs', [])

# Set datasource UID directly (will be resolved on import)
# Replace template variable with actual datasource uid
ds_uid = 'sensor-platform-postgres'

def replace_ds(obj):
    if isinstance(obj, dict):
        if obj.get('uid') == '\${DS_POSTGRESQL}':
            obj['uid'] = ds_uid
        for v in obj.values():
            replace_ds(v)
    elif isinstance(obj, list):
        for item in obj:
            replace_ds(item)

replace_ds(dashboard)

# Wrap for /api/dashboards/db endpoint
payload = {
    'dashboard': dashboard,
    'overwrite': True,
    'message': 'Deployed from deploy-dashboard.sh'
}

print(json.dumps(payload))
")

# --- Step 2: Ensure PostgreSQL datasource exists on remote ---
echo "📡 Step 2: Creating/updating PostgreSQL datasource..."

DATASOURCE_JSON=$(cat <<'EOF'
{
  "name": "Sensor Platform PostgreSQL",
  "uid": "sensor-platform-postgres",
  "type": "postgres",
  "url": "postgres:5432",
  "database": "sensor_platform",
  "user": "postgres",
  "secureJsonData": {
    "password": "postgres"
  },
  "jsonData": {
    "sslmode": "disable",
    "maxOpenConns": 10,
    "maxIdleConns": 2,
    "connMaxLifetime": 14400,
    "postgresVersion": 1500,
    "timescaledb": false
  },
  "access": "proxy",
  "isDefault": false
}
EOF
)

# Copy files and run commands on remote
echo "📤 Step 3: Deploying to remote server..."

# Create temp files on remote and import via Grafana API
${SSH_CMD} bash -s <<REMOTE_SCRIPT
set -euo pipefail

GRAFANA_URL="${GRAFANA_URL}"
GRAFANA_AUTH="${GRAFANA_USER}:${GRAFANA_PASS}"

echo "  → Checking Grafana is accessible..."
HTTP_CODE=\$(curl -s -o /dev/null -w "%{http_code}" "\${GRAFANA_URL}/api/health" 2>/dev/null || echo "000")
if [ "\${HTTP_CODE}" != "200" ]; then
    echo "  ⚠️  Grafana not responding at \${GRAFANA_URL} (HTTP \${HTTP_CODE})"
    echo "  Trying to find Grafana container..."
    GRAFANA_CONTAINER=\$(docker ps --filter "ancestor=grafana/grafana" --format "{{.Names}}" 2>/dev/null | head -1)
    if [ -z "\${GRAFANA_CONTAINER}" ]; then
        GRAFANA_CONTAINER=\$(docker ps --filter "name=grafana" --format "{{.Names}}" 2>/dev/null | head -1)
    fi
    if [ -n "\${GRAFANA_CONTAINER}" ]; then
        GRAFANA_PORT=\$(docker port "\${GRAFANA_CONTAINER}" 3000 2>/dev/null | head -1 | cut -d: -f2)
        GRAFANA_URL="http://localhost:\${GRAFANA_PORT:-3000}"
        echo "  → Found Grafana at \${GRAFANA_URL}"
    else
        echo "  ❌ Cannot find Grafana. Please ensure it's running."
        exit 1
    fi
fi

echo "  → Creating PostgreSQL datasource..."
curl -s -X POST "\${GRAFANA_URL}/api/datasources" \
  -H "Content-Type: application/json" \
  -u "\${GRAFANA_AUTH}" \
  -d '${DATASOURCE_JSON}' 2>/dev/null | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin)
    if 'id' in r:
        print('    ✅ Datasource created (id: {})'.format(r['id']))
    elif 'message' in r and 'already exists' in r['message']:
        print('    ℹ️  Datasource already exists, updating...')
    else:
        print('    ℹ️  ' + r.get('message', str(r)))
except:
    print('    ⚠️  Could not parse response')
" 2>/dev/null || echo "    ⚠️  Datasource creation returned non-JSON"

# Update datasource if it already exists
curl -s -X PUT "\${GRAFANA_URL}/api/datasources/uid/sensor-platform-postgres" \
  -H "Content-Type: application/json" \
  -u "\${GRAFANA_AUTH}" \
  -d '${DATASOURCE_JSON}' 2>/dev/null > /dev/null || true

echo "  → Importing dashboard..."
REMOTE_SCRIPT

# Now send the dashboard payload
echo "${IMPORT_PAYLOAD}" | ${SSH_CMD} bash -c "
GRAFANA_URL='${GRAFANA_URL}'
GRAFANA_AUTH='${GRAFANA_USER}:${GRAFANA_PASS}'

# Try to detect Grafana URL
HTTP_CODE=\$(curl -s -o /dev/null -w '%{http_code}' \"\${GRAFANA_URL}/api/health\" 2>/dev/null || echo '000')
if [ \"\${HTTP_CODE}\" != '200' ]; then
    GRAFANA_CONTAINER=\$(docker ps --filter 'name=grafana' --format '{{.Names}}' 2>/dev/null | head -1)
    if [ -n \"\${GRAFANA_CONTAINER}\" ]; then
        GRAFANA_PORT=\$(docker port \"\${GRAFANA_CONTAINER}\" 3000 2>/dev/null | head -1 | cut -d: -f2)
        GRAFANA_URL=\"http://localhost:\${GRAFANA_PORT:-3000}\"
    fi
fi

cat - | curl -s -X POST \"\${GRAFANA_URL}/api/dashboards/db\" \
  -H 'Content-Type: application/json' \
  -u \"\${GRAFANA_AUTH}\" \
  -d @- | python3 -c \"
import sys, json
try:
    r = json.load(sys.stdin)
    if r.get('status') == 'success' or 'uid' in r:
        print('    ✅ Dashboard imported successfully!')
        print('    🔗 URL: ' + r.get('url', '/d/home-sensors-main'))
    else:
        print('    ❌ ' + r.get('message', str(r)))
except Exception as e:
    print('    ⚠️  Response parse error: ' + str(e))
\" 2>/dev/null
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Done! Open Grafana → Dashboards → 🏠 Home Sensors"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

