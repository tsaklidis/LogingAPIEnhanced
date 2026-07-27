#!/bin/bash
# deploy.sh — Pull latest code from GitHub and redeploy
#
# ⚠️  IMPORTANT: Do NOT manually edit files on the server (rsync, nano, etc.)
# that are tracked by git. The GitHub Actions deploy pulls from origin/main
# and will FAIL if there are uncommitted local changes. All code changes
# must go through git push → GitHub Actions.
#
set -e

cd /home/dulano/sensor-platform
export DOCKER_CONFIG=/home/dulano/.docker

echo "📥 Pulling latest code from GitHub..."
git reset --hard origin/main 2>/dev/null || true
git pull origin main

echo ""
echo "🔨 Building Docker image..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml build web

echo ""
echo "🚀 Restarting services..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d web celery celery-beat

echo ""
echo "⏳ Waiting for health check..."
sleep 10
STATUS=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: logs.tsaklidis.gr' http://127.0.0.1:8080/api/v1/health/)

if [ "$STATUS" = "200" ]; then
    echo "✅ Deploy successful! App is healthy."
else
    echo "⚠️  App returned HTTP $STATUS — check logs:"
    echo "   docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=20 web"
fi

