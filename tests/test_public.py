import pytest
from django.urls import reverse
from rest_framework import status

from tests.factories import SensorFactory, SensorReadingFactory, SpaceFactory


@pytest.mark.django_db
class TestPublicEndpoints:
    def test_public_latest_reading(self, api_client):
        space = SpaceFactory(is_public=True)
        sensor = SensorFactory(space=space)
        SensorReadingFactory(sensor=sensor)
        response = api_client.get(
            reverse('sensors:public-sensor-readings-latest', kwargs={'sensor_pk': sensor.pk}),
        )
        assert response.status_code == status.HTTP_200_OK

    def test_private_sensor_latest_not_accessible(self, api_client):
        space = SpaceFactory(is_public=False)
        sensor = SensorFactory(space=space)
        SensorReadingFactory(sensor=sensor)
        response = api_client.get(
            reverse('sensors:public-sensor-readings-latest', kwargs={'sensor_pk': sensor.pk}),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

