from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import PublicDashboardView

urlpatterns = [
    # Public dashboard (root)
    path('', PublicDashboardView.as_view(), name='public-dashboard'),
    path('admin/', admin.site.urls),
    # API v1
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.homes.urls')),
    path('api/v1/', include('apps.sensors.urls')),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Health check
    path('api/v1/health/', include('apps.common.urls')),
]

