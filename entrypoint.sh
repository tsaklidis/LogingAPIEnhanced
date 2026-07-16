#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until python -c "
import psycopg
psycopg.connect(
    dbname='${DB_NAME}',
    user='${DB_USER}',
    password='${DB_PASSWORD}',
    host='${DB_HOST}',
    port='${DB_PORT}'
)
" 2>/dev/null; do
    echo "  PostgreSQL not ready, retrying..."
    sleep 2
done
echo "PostgreSQL is ready."

echo "Applying migrations..."
python manage.py migrate --noinput || echo "Warning: migrations failed (may need makemigrations first)"

echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

exec "$@"


