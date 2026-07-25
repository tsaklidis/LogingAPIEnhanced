from django.urls import path

from . import views

app_name = 'sensors'

urlpatterns = [
    # Sensor management
    path('spaces/<uuid:space_pk>/sensors/', views.SensorListCreateView.as_view(), name='sensor-list'),
    path('sensors/<uuid:pk>/', views.SensorDetailView.as_view(), name='sensor-detail'),
    path('sensors/<uuid:pk>/rotate-key/', views.SensorRotateKeyView.as_view(), name='sensor-rotate-key'),
    # Per-sensor ingestion (X-Sensor-Key)
    path('ingest/', views.IngestView.as_view(), name='ingest'),
    path('ingest/bulk/', views.BulkIngestView.as_view(), name='ingest-bulk'),
    # Gateway ingestion (X-Gateway-Key — one key per home, multiple sensors)
    path('ingest/gateway/', views.GatewayIngestView.as_view(), name='ingest-gateway'),
    # Home gateway key management
    path('homes/<uuid:pk>/gateway-key/', views.HomeGatewayKeyView.as_view(), name='home-gateway-key'),
    # Readings
    path('sensors/<uuid:sensor_pk>/readings/', views.SensorReadingListView.as_view(), name='sensor-readings'),
    path('sensors/<uuid:sensor_pk>/readings/latest/', views.SensorReadingLatestView.as_view(), name='sensor-readings-latest'),
    # Public
    path('public/sensors/', views.PublicSensorListView.as_view(), name='public-sensor-list'),
    path('public/sensors/<uuid:sensor_pk>/readings/', views.PublicSensorReadingListView.as_view(), name='public-sensor-readings'),
    path('public/sensors/<uuid:sensor_pk>/readings/latest/', views.PublicSensorReadingLatestView.as_view(), name='public-sensor-readings-latest'),
]

