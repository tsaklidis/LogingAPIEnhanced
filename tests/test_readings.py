import pytest
from django.urls import reverse
from rest_framework import status

from tests.factories import SensorReadingFactory, UserFactory


@pytest.mark.django_db
class TestReadings:
    def test_list_readings(self, authenticated_client, sensor):
        SensorReadingFactory.create_batch(5, sensor=sensor)
        response = authenticated_client.get(
            reverse('sensors:sensor-readings', kwargs={'sensor_pk': sensor.pk}),
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5

    def test_latest_reading(self, authenticated_client, sensor):
        SensorReadingFactory.create_batch(3, sensor=sensor)
        response = authenticated_client.get(
            reverse('sensors:sensor-readings-latest', kwargs={'sensor_pk': sensor.pk}),
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data

    def test_cannot_read_others_sensor(self, api_client, sensor):
        other_user = UserFactory()
        api_client.force_authenticate(user=other_user)
        response = api_client.get(
            reverse('sensors:sensor-readings', kwargs={'sensor_pk': sensor.pk}),
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0


@pytest.mark.django_db
class TestPublicReadings:
    def test_public_sensor_readings(self, api_client, sensor):
        sensor.space.is_public = True
        sensor.space.save()
        SensorReadingFactory.create_batch(3, sensor=sensor)
        response = api_client.get(
            reverse('sensors:public-sensor-readings', kwargs={'sensor_pk': sensor.pk}),
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_private_sensor_not_accessible(self, api_client, sensor):
        SensorReadingFactory.create_batch(3, sensor=sensor)
        response = api_client.get(
            reverse('sensors:public-sensor-readings', kwargs={'sensor_pk': sensor.pk}),
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0

