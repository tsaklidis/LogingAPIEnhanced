from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import IsAdminUser

from apps.common.views import PublicDashboardView

urlpatterns = [
    # Public dashboard (root)
    path("", PublicDashboardView.as_view(), name="public-dashboard"),
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.homes.urls")),
    path("api/v1/", include("apps.sensors.urls")),
    # API Documentation (admin only)
    path("api/schema/", SpectacularAPIView.as_view(permission_classes=[IsAdminUser]), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[IsAdminUser]),
        name="swagger-ui",
    ),
    # Health check
    path("api/v1/health/", include("apps.common.urls")),
]
