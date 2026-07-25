import pytest
from rest_framework.test import APIClient

from tests.factories import HomeFactory, HomeWithGatewayFactory, SensorFactory, SpaceFactory, UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    api_client.user = user
    return api_client


@pytest.fixture
def home(user):
    return HomeFactory(owner=user)


@pytest.fixture
def space(home):
    return SpaceFactory(home=home)


@pytest.fixture
def sensor(space):
    return SensorFactory(space=space)


@pytest.fixture
def sensor_with_key(sensor):
    """A sensor ready for ingestion tests."""
    return sensor


@pytest.fixture
def home_with_gateway(user):
    """A home with a gateway API key for gateway ingestion tests."""
    return HomeWithGatewayFactory(owner=user)


@pytest.fixture
def gateway_setup(home_with_gateway):
    """A full gateway setup: home with key + 2 spaces + 3 sensors."""
    space1 = SpaceFactory(home=home_with_gateway, name="Living Room")
    space2 = SpaceFactory(home=home_with_gateway, name="Bedroom")
    sensor1 = SensorFactory(space=space1, name="Temp Living", sensor_type="DHT22")
    sensor2 = SensorFactory(space=space1, name="Air Quality", sensor_type="BME280")
    sensor3 = SensorFactory(space=space2, name="Temp Bedroom", sensor_type="DHT22")
    return {
        "home": home_with_gateway,
        "spaces": [space1, space2],
        "sensors": [sensor1, sensor2, sensor3],
    }
