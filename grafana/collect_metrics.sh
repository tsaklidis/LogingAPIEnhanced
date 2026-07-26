#!/bin/bash
# System & Docker metrics collector - writes to PostgreSQL every minute
# Run via cron: * * * * * /home/dulano/sensor-platform/collect_metrics.sh

DB_CONTAINER="sensor-platform-db-1"
DB_USER="sensor_user"
DB_NAME="sensor_platform"

psql_exec() {
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "$1" > /dev/null 2>&1
}

NOW=$(date -u +"%Y-%m-%d %H:%M:%S+00")

# --- System CPU ---
CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}' | cut -d. -f1)
CPU_USED=$((100 - ${CPU_IDLE:-0}))

# --- System Memory ---
MEM_TOTAL=$(free -m | awk '/Mem:/ {print $2}')
MEM_USED=$(free -m | awk '/Mem:/ {print $3}')
MEM_AVAIL=$(free -m | awk '/Mem:/ {print $7}')
MEM_PCT=$(awk "BEGIN {printf \"%.1f\", ($MEM_USED/$MEM_TOTAL)*100}")

# --- Swap ---
SWAP_TOTAL=$(free -m | awk '/Swap:/ {print $2}')
SWAP_USED=$(free -m | awk '/Swap:/ {print $3}')
SWAP_PCT=0
if [ "$SWAP_TOTAL" -gt 0 ] 2>/dev/null; then
    SWAP_PCT=$(awk "BEGIN {printf \"%.1f\", ($SWAP_USED/$SWAP_TOTAL)*100}")
fi

# --- Disk ---
DISK_PCT=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
DISK_USED=$(df -m / | awk 'NR==2 {print $3}')
DISK_TOTAL=$(df -m / | awk 'NR==2 {print $2}')

# --- Load Average ---
LOAD1=$(awk '{print $1}' /proc/loadavg)
LOAD5=$(awk '{print $2}' /proc/loadavg)
LOAD15=$(awk '{print $3}' /proc/loadavg)

# Insert system metrics
psql_exec "INSERT INTO system_metrics (recorded_at, metric_type, metric_name, metric_value) VALUES
  ('$NOW', 'cpu', 'usage_percent', $CPU_USED),
  ('$NOW', 'memory', 'used_mb', $MEM_USED),
  ('$NOW', 'memory', 'total_mb', $MEM_TOTAL),
  ('$NOW', 'memory', 'usage_percent', $MEM_PCT),
  ('$NOW', 'memory', 'available_mb', $MEM_AVAIL),
  ('$NOW', 'swap', 'used_mb', $SWAP_USED),
  ('$NOW', 'swap', 'total_mb', $SWAP_TOTAL),
  ('$NOW', 'swap', 'usage_percent', $SWAP_PCT),
  ('$NOW', 'disk', 'usage_percent', $DISK_PCT),
  ('$NOW', 'disk', 'used_mb', $DISK_USED),
  ('$NOW', 'disk', 'total_mb', $DISK_TOTAL),
  ('$NOW', 'load', '1min', $LOAD1),
  ('$NOW', 'load', '5min', $LOAD5),
  ('$NOW', 'load', '15min', $LOAD15);"

# --- Docker container stats ---
docker stats --no-stream --format "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}" 2>/dev/null | grep "sensor-platform" | while IFS='|' read -r NAME CPU MEM_USAGE MEM_PERC; do
    CPU_VAL=$(echo "$CPU" | tr -d '% ')
    MEM_PERC_VAL=$(echo "$MEM_PERC" | tr -d '% ')
    MEM_USED_VAL=$(echo "$MEM_USAGE" | awk -F/ '{print $1}' | tr -d ' ')

    # Convert memory to MB
    if echo "$MEM_USED_VAL" | grep -qi "gib"; then
        MEM_MB=$(echo "$MEM_USED_VAL" | sed 's/[^0-9.]//g' | awk '{printf "%.1f", $1*1024}')
    elif echo "$MEM_USED_VAL" | grep -qi "kib"; then
        MEM_MB=$(echo "$MEM_USED_VAL" | sed 's/[^0-9.]//g' | awk '{printf "%.1f", $1/1024}')
    else
        MEM_MB=$(echo "$MEM_USED_VAL" | sed 's/[^0-9.]//g' | awk '{printf "%.1f", $1}')
    fi

    # Short container name
    SHORT_NAME=$(echo "$NAME" | sed 's/sensor-platform-//;s/-1$//')

    psql_exec "INSERT INTO system_metrics (recorded_at, metric_type, metric_name, metric_value) VALUES
      ('$NOW', 'docker_cpu', '$SHORT_NAME', $CPU_VAL),
      ('$NOW', 'docker_mem_mb', '$SHORT_NAME', $MEM_MB),
      ('$NOW', 'docker_mem_pct', '$SHORT_NAME', $MEM_PERC_VAL);"
done

# --- Cleanup old metrics (keep 7 days) ---
psql_exec "DELETE FROM system_metrics WHERE recorded_at < NOW() - INTERVAL '7 days';"

