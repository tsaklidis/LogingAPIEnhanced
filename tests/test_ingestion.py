import pytest
from django.urls import reverse
from rest_framework import status

from apps.sensors.models import SensorReading


@pytest.mark.django_db
class TestIngestion:
    def test_single_ingest(self, api_client, sensor_with_key):
        api_client.credentials(HTTP_X_SENSOR_KEY=sensor_with_key._raw_api_key)
        response = api_client.post(
            reverse('sensors:ingest'),
            {'data': {'temperature': 25.6, 'humidity': 48.2}},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert SensorReading.objects.count() == 1

    def test_single_ingest_with_timestamp(self, api_client, sensor_with_key):
        api_client.credentials(HTTP_X_SENSOR_KEY=sensor_with_key._raw_api_key)
        response = api_client.post(
            reverse('sensors:ingest'),
            {
                'data': {'temperature': 25.6},
                'recorded_at': '2026-07-15T10:30:00Z',
            },
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_bulk_ingest(self, api_client, sensor_with_key):
        api_client.credentials(HTTP_X_SENSOR_KEY=sensor_with_key._raw_api_key)
        response = api_client.post(
            reverse('sensors:ingest-bulk'),
            [
                {'data': {'temperature': 25.6}},
                {'data': {'temperature': 25.8}},
                {'data': {'temperature': 26.0}},
            ],
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['count'] == 3
        assert SensorReading.objects.count() == 3

    def test_ingest_invalid_sensor_key(self, api_client):
        api_client.credentials(HTTP_X_SENSOR_KEY='invalid-key')
        response = api_client.post(
            reverse('sensors:ingest'),
            {'data': {'temperature': 25.6}},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_ingest_future_timestamp_rejected(self, api_client, sensor_with_key):
        api_client.credentials(HTTP_X_SENSOR_KEY=sensor_with_key._raw_api_key)
        response = api_client.post(
            reverse('sensors:ingest'),
            {
                'data': {'temperature': 25.6},
                'recorded_at': '2027-01-01T00:00:00Z',
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ingest_empty_data_rejected(self, api_client, sensor_with_key):
        api_client.credentials(HTTP_X_SENSOR_KEY=sensor_with_key._raw_api_key)
        response = api_client.post(
            reverse('sensors:ingest'),
            {'data': {}},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

