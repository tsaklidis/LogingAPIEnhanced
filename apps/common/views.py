from django.core.cache import cache
from django.db import connection
from django.views.generic import TemplateView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class PublicDashboardView(TemplateView):
    """Public-facing dashboard showing sensor data."""

    template_name = "public/dashboard.html"


class HealthCheckView(APIView):
    """Health check endpoint for monitoring and Docker healthchecks."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        health = {"status": "healthy", "checks": {}}

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health["checks"]["database"] = "ok"
        except Exception as e:
            health["checks"]["database"] = f"error: {str(e)}"
            health["status"] = "unhealthy"

        # Check Redis cache
        try:
            cache.set("health_check", "ok", timeout=5)
            if cache.get("health_check") == "ok":
                health["checks"]["cache"] = "ok"
            else:
                health["checks"]["cache"] = "error: could not read back"
                health["status"] = "unhealthy"
        except Exception as e:
            health["checks"]["cache"] = f"error: {str(e)}"
            health["status"] = "unhealthy"

        status_code = status.HTTP_200_OK if health["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health, status=status_code)
