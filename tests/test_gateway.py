import pytest
from django.urls import reverse
from rest_framework import status

from apps.sensors.models import SensorReading
from tests.factories import HomeWithGatewayFactory, SensorFactory, SpaceFactory


@pytest.mark.django_db
class TestGatewayIngestion:
    def test_gateway_ingest_multiple_sensors(self, api_client, gateway_setup):
        """A gateway sends data for multiple sensors in one request."""
        home = gateway_setup['home']
        sensors = gateway_setup['sensors']

        api_client.credentials(HTTP_X_GATEWAY_KEY=home._raw_api_key)
        response = api_client.post(
            reverse('sensors:ingest-gateway'),
            {
                'readings': [
                    {'sensor_id': str(sensors[0].id), 'data': {'temperature': 25.6, 'humidity': 48.2}},
                    {'sensor_id': str(sensors[1].id), 'data': {'co2': 412, 'tvoc': 15}},
                    {'sensor_id': str(sensors[2].id), 'data': {'temperature': 22.1, 'humidity': 55.0}},
                ]
            },
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['count'] == 3
        assert response.data['sensors'] == 3
        assert SensorReading.objects.count() == 3

    def test_gateway_ingest_multiple_readings_same_sensor(self, api_client, gateway_setup):
        """A gateway sends multiple buffered readings for the same sensor."""
        home = gateway_setup['home']
        sensor = gateway_setup['sensors'][0]

        api_client.credentials(HTTP_X_GATEWAY_KEY=home._raw_api_key)
        response = api_client.post(
            reverse('sensors:ingest-gateway'),
            {
                'readings': [
                    {'sensor_id': str(sensor.id), 'data': {'temperature': 25.0}, 'recorded_at': '2026-07-16T10:00:00Z'},
                    {'sensor_id': str(sensor.id), 'data': {'temperature': 25.5}, 'recorded_at': '2026-07-16T10:01:00Z'},
                    {'sensor_id': str(sensor.id), 'data': {'temperature': 26.0}, 'recorded_at': '2026-07-16T10:02:00Z'},
                ]
            },
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['count'] == 3
        assert response.data['sensors'] == 1

    def test_gateway_rejects_sensor_from_other_home(self, api_client, gateway_setup):
        """A gateway cannot ingest data for sensors that don't belong to its home."""
        home = gateway_setup['home']
        other_home = HomeWithGatewayFactory()
        other_space = SpaceFactory(home=other_home)
        other_sensor = SensorFactory(space=other_space)

        api_client.credentials(HTTP_X_GATEWAY_KEY=home._raw_api_key)
        response = api_client.post(
            reverse('sensors:ingest-gateway'),
            {
                'readings': [
                    {'sensor_id': str(other_sensor.id), 'data': {'temperature': 25.6}},
                ]
            },
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'invalid_sensor_ids' in response.data
        assert SensorReading.objects.count() == 0

    def test_gateway_rejects_invalid_key(self, api_client):
        """Invalid gateway key is rejected."""
        api_client.credentials(HTTP_X_GATEWAY_KEY='invalid-key')
        response = api_client.post(
            reverse('sensors:ingest-gateway'),
            {
                'readings': [
                    {'sensor_id': '00000000-0000-0000-0000-000000000000', 'data': {'temperature': 25.6}},
                ]
            },
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_gateway_rejects_empty_readings(self, api_client, gateway_setup):
        """Empty readings list is rejected."""
        home = gateway_setup['home']
        api_client.credentials(HTTP_X_GATEWAY_KEY=home._raw_api_key)
        response = api_client.post(
            reverse('sensors:ingest-gateway'),
            {'readings': []},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_gateway_rejects_jwt_auth(self, authenticated_client):
        """Gateway endpoint rejects JWT auth — must use X-Gateway-Key."""
        response = authenticated_client.post(
            reverse('sensors:ingest-gateway'),
            {
                'readings': [
                    {'sensor_id': '00000000-0000-0000-0000-000000000000', 'data': {'temperature': 25.6}},
                ]
            },
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_rotated_key_invalidates_old(self, api_client, authenticated_client, home):
        """After rotating, the old key no longer works."""
        # Generate first key
        resp1 = authenticated_client.post(
            reverse('sensors:home-gateway-key', kwargs={'pk': home.pk}),
        )
        old_key = resp1.data['api_key']

        # Rotate to new key
        resp2 = authenticated_client.post(
            reverse('sensors:home-gateway-key', kwargs={'pk': home.pk}),
        )
        new_key = resp2.data['api_key']

        # Create a sensor to ingest into
        space = SpaceFactory(home=home)
        sensor = SensorFactory(space=space)

        # Old key should fail
        api_client.credentials(HTTP_X_GATEWAY_KEY=old_key)
        response = api_client.post(
            reverse('sensors:ingest-gateway'),
            {'readings': [{'sensor_id': str(sensor.id), 'data': {'temperature': 25.6}}]},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # New key should work
        api_client.credentials(HTTP_X_GATEWAY_KEY=new_key)
        response = api_client.post(
            reverse('sensors:ingest-gateway'),
            {'readings': [{'sensor_id': str(sensor.id), 'data': {'temperature': 25.6}}]},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestHomeGatewayKeyManagement:
    def test_generate_gateway_key(self, authenticated_client, home):
        """Owner can generate a gateway key for their home."""
        response = authenticated_client.post(
            reverse('sensors:home-gateway-key', kwargs={'pk': home.pk}),
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'api_key' in response.data
        assert '.' in response.data['api_key']  # prefix.secret format
        assert len(response.data['api_key']) > 40

    def test_rotate_gateway_key(self, authenticated_client, home):
        """Generating a new key replaces the old one."""
        resp1 = authenticated_client.post(
            reverse('sensors:home-gateway-key', kwargs={'pk': home.pk}),
        )
        first_key = resp1.data['api_key']

        resp2 = authenticated_client.post(
            reverse('sensors:home-gateway-key', kwargs={'pk': home.pk}),
        )
        second_key = resp2.data['api_key']
        assert first_key != second_key

    def test_revoke_gateway_key(self, authenticated_client):
        """Owner can revoke (delete) the gateway key."""
        home = HomeWithGatewayFactory(owner=authenticated_client.user)
        response = authenticated_client.delete(
            reverse('sensors:home-gateway-key', kwargs={'pk': home.pk}),
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        home.refresh_from_db()
        assert home.key_hash == ''
        assert home.key_prefix == ''

    def test_cannot_manage_others_gateway_key(self, authenticated_client):
        """Cannot generate a key for another user's home."""
        other_home = HomeWithGatewayFactory()
        response = authenticated_client.post(
            reverse('sensors:home-gateway-key', kwargs={'pk': other_home.pk}),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

