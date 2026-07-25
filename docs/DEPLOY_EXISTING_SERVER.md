# Deployment Guide — Existing Server (Alongside Other Services)

> **Target**: Ubuntu server already running Nginx, another Django app via uWSGI (bare-metal, no Docker).  
> **Strategy**: Docker Compose for isolation — avoids Python/package conflicts with the existing app.  
> **Traffic flow**: Existing Nginx → reverse-proxy → Docker container (uWSGI socket exposed on a port).

---

## 🚀 Quick Start

```bash
# 1. Copy project to server
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '.venv' \
    . root@YOUR_SERVER_IP:/opt/sensor-platform/

# 2. SSH in
ssh root@YOUR_SERVER_IP

# 3. Create .env file (see section 3 below)
nano /opt/sensor-platform/.env

# 4. Start the stack
cd /opt/sensor-platform
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 5. Create admin user
docker compose exec web python manage.py createsuperuser

# 6. Add Nginx vhost (see section 5 below)
```

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Install Docker (if not installed)](#2-install-docker)
3. [Configure Environment](#3-configure-environment)
4. [Deploy with Docker Compose](#4-deploy-with-docker-compose)
5. [Configure Existing Nginx](#5-configure-existing-nginx)
6. [HTTPS with Certbot](#6-https-with-certbot)
7. [Maintenance & Operations](#7-maintenance--operations)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prerequisites

### What's already on the server

| Service | Status | Impact |
|---------|--------|--------|
| **Nginx** | Running on port 80/443 | We'll add a new `server` block — no conflict |
| **Django + uWSGI** | Running (bare-metal) | Completely isolated — our app runs in Docker |
| **PostgreSQL** | May or may not exist | Our app uses its own Postgres inside Docker |
| **Redis** | May or may not exist | Our app uses its own Redis inside Docker |

### Architecture

```
Internet
   │
   ▼ (port 80/443)
┌───────────────────────────────────────────────────────────────────┐
│  Existing Nginx                                                   │
│                                                                   │
│  server_name existing-app.com → uwsgi_pass to existing app       │
│  server_name sensors.your-domain.com → proxy_pass :8080 ──┐      │
│                                                            │      │
│  ┌─────────────── Docker Compose ──────────────────────┐   │      │
│  │                                                     │   │      │
│  │  Nginx (container, port 8080) ◀─────────────────────┘   │      │
│  │       │                                             │         │
│  │       ▼ uwsgi_pass                                  │         │
│  │  Django/uWSGI (port 8000 internal)                  │         │
│  │       │                                             │         │
│  │       ▼                                             │         │
│  │  PostgreSQL (5433:5432)    Redis (6380:6379)        │         │
│  │  Celery Worker + Beat                               │         │
│  │                                                     │         │
│  └─────────────────────────────────────────────────────┘         │
└───────────────────────────────────────────────────────────────────┘
```

> **Key**: Docker services use non-standard host ports (8080, 5433, 6380) to avoid conflicts with anything already running on the server.

---

## 2. Install Docker (if not installed)

Check if Docker is already installed:

```bash
docker --version && docker compose version
```

If not installed:

```bash
# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine + Compose plugin
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify
docker compose version
```

---

## 3. Configure Environment

### 3.1 Create the `.env` file

```bash
cd /opt/sensor-platform
nano .env
```

Paste the following (fill in the values):

```bash
# Django
SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_urlsafe(50))">
DEBUG=False
ALLOWED_HOSTS=sensors.your-domain.com,YOUR_SERVER_IP
DJANGO_SETTINGS_MODULE=config.settings.prod

# Database (internal Docker network — no conflict with host PostgreSQL)
DB_NAME=sensor_platform
DB_USER=sensor_user
DB_PASSWORD=<generate with: openssl rand -base64 32>
DB_HOST=db
DB_PORT=5432

# Redis (internal Docker network)
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

### 3.2 Set proper permissions

```bash
chmod 600 /opt/sensor-platform/.env
```

---

## 4. Deploy with Docker Compose

### 4.1 Create the production override file

This overrides the default `docker-compose.yml` with production-appropriate settings and safe port mappings:

```bash
cat > /opt/sensor-platform/docker-compose.prod.yml << 'EOF'
# docker-compose.prod.yml — Production overrides for existing server deployment
services:
  web:
    build:
      context: .
      args:
        INSTALL_DEV: "false"
    command: uwsgi --ini config/uwsgi.ini
    restart: unless-stopped
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod
    volumes:
      - static_files:/app/staticfiles
    # No ports exposed to host — Nginx container handles it

  db:
    restart: unless-stopped
    ports:
      - "127.0.0.1:5433:5432"   # Expose on localhost:5433 for debugging only
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    restart: unless-stopped
    ports:
      - "127.0.0.1:6380:6379"   # Expose on localhost:6380 for debugging only

  celery:
    build:
      context: .
      args:
        INSTALL_DEV: "false"
    restart: unless-stopped
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod

  celery-beat:
    build:
      context: .
      args:
        INSTALL_DEV: "false"
    restart: unless-stopped
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod

  nginx:
    ports:
      - "127.0.0.1:8080:80"    # Only on localhost — host Nginx will proxy to this
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - static_files:/app/staticfiles:ro
    restart: unless-stopped

volumes:
  pgdata:
  static_files:
EOF
```

### 4.2 Build and start

```bash
cd /opt/sensor-platform

# Build images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start all services (detached)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check everything is running
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

All containers should show `Up (healthy)` or `Up`.

### 4.3 Verify the app responds

```bash
curl -s http://127.0.0.1:8080/api/v1/health/ | python3 -m json.tool
```

### 4.4 Create admin user

```bash
cd /opt/sensor-platform
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

---

## 5. Configure Existing Nginx

Add a new server block to your existing Nginx installation. This runs **alongside** your other sites.

### 5.1 Create the vhost config

```bash
nano /etc/nginx/sites-available/sensor-platform
```

**Option A — With a subdomain** (e.g., `sensors.your-domain.com`):

```nginx
upstream sensor_platform {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name sensors.your-domain.com;

    client_max_body_size 10M;

    # Proxy everything to the Docker Nginx container
    location / {
        proxy_pass http://sensor_platform;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Option B — With a URL prefix** (e.g., `your-domain.com/sensors/`):

> ⚠️ This requires Django `FORCE_SCRIPT_NAME` configuration. Option A is simpler.

```nginx
# Add this location block INSIDE your existing server { } block:

location /sensors/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header SCRIPT_NAME /sensors;
}
```

### 5.2 Enable the site and reload

```bash
ln -s /etc/nginx/sites-available/sensor-platform /etc/nginx/sites-enabled/

# Test config (must show "syntax is ok")
nginx -t

# Reload without downtime
systemctl reload nginx
```

### 5.3 Test

```bash
curl http://sensors.your-domain.com/api/v1/health/
```

---

## 6. HTTPS with Certbot

Since you already have Nginx with other sites, you likely have Certbot installed. If not:

```bash
apt-get install -y certbot python3-certbot-nginx
```

Issue a certificate for the sensor platform subdomain:

```bash
certbot --nginx -d sensors.your-domain.com
```

Certbot will automatically modify your Nginx config to add SSL. Verify:

```bash
curl https://sensors.your-domain.com/api/v1/health/
```

---

## 7. Maintenance & Operations

### Create a convenience alias

```bash
echo 'alias sensor-compose="cd /opt/sensor-platform && docker compose -f docker-compose.yml -f docker-compose.prod.yml"' >> ~/.bashrc
source ~/.bashrc
```

Now you can use `sensor-compose` instead of the long command.

### Update the application (new code)

From your **local machine**:
```bash
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '.venv' \
    . root@YOUR_SERVER_IP:/opt/sensor-platform/
```

Then on the **server**:
```bash
cd /opt/sensor-platform
docker compose -f docker-compose.yml -f docker-compose.prod.yml build web
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d web celery celery-beat
```

### View logs

```bash
cd /opt/sensor-platform

# Django/uWSGI logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web

# Celery worker
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f celery

# All services
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### Run Django management commands

```bash
cd /opt/sensor-platform

# Migrations
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate

# Django shell
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py shell

# Any command
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py <command>
```

### Database backup

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec db \
    pg_dump -U sensor_user sensor_platform | gzip > /opt/backups/sensor_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Database restore

```bash
gunzip < backup.sql.gz | docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
    psql -U sensor_user sensor_platform
```

### Restart services

```bash
cd /opt/sensor-platform

# Restart everything
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart

# Restart only Django
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

### Stop everything (without data loss)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
# Data is preserved in Docker volumes (pgdata, static_files)
```

### Full cleanup (⚠️ deletes data)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```

---

## 8. Troubleshooting

### Container won't start / CrashLoopBackOff

```bash
# Check logs for the failing service
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs web

# Common causes:
# - Wrong DB_PASSWORD in .env
# - Missing .env file
# - PostgreSQL not ready yet (entrypoint.sh will retry)
```

### Port conflict on 8080

If something else uses port 8080, change it in `docker-compose.prod.yml`:

```yaml
  nginx:
    ports:
      - "127.0.0.1:9090:80"    # Use any free port
```

Then update the Nginx vhost to match:
```nginx
upstream sensor_platform {
    server 127.0.0.1:9090;
}
```

### Existing Nginx can't reach Docker container

```bash
# Verify the container Nginx is listening
curl -s http://127.0.0.1:8080/api/v1/health/

# If nothing: check docker compose ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# If port shows but no response: check internal nginx → uwsgi
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs web
```

### Static files not loading

```bash
# Re-collect static files
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### Database connection from host (for debugging)

```bash
# Connect to the containerized PostgreSQL from the host
psql -h 127.0.0.1 -p 5433 -U sensor_user sensor_platform
```

### Auto-start on server reboot

Docker services with `restart: unless-stopped` will auto-start when Docker starts. Ensure Docker is enabled:

```bash
systemctl enable docker
```

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Start all | `sensor-compose up -d` |
| Stop all | `sensor-compose down` |
| View logs | `sensor-compose logs -f` |
| Rebuild & deploy | `sensor-compose build && sensor-compose up -d` |
| Run migrations | `sensor-compose exec web python manage.py migrate` |
| Create superuser | `sensor-compose exec web python manage.py createsuperuser` |
| Django shell | `sensor-compose exec web python manage.py shell` |
| DB backup | `sensor-compose exec db pg_dump -U sensor_user sensor_platform > backup.sql` |
| Restart Django | `sensor-compose restart web` |
| Check status | `sensor-compose ps` |

> **Note**: `sensor-compose` is the alias defined in section 7. Replace with the full `cd /opt/sensor-platform && docker compose -f docker-compose.yml -f docker-compose.prod.yml` if you haven't set it up.

