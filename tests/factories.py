
import factory
from django.utils import timezone

from apps.accounts.models import User
from apps.common.apikey import generate_key
from apps.homes.models import Home, Space
from apps.sensors.models import Sensor, SensorReading


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


def _make_key():
    """Generate a key and return (prefix, hash). Stash raw key on the tuple for tests."""
    raw_key, prefix, key_hash = generate_key()
    return raw_key, prefix, key_hash


class HomeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Home
        exclude = ['_key_data']

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Home {n}')
    location = factory.Faker('address')
    key_prefix = ''
    key_hash = ''


class HomeWithGatewayFactory(HomeFactory):
    """Home with a pre-generated gateway API key."""
    _key_data = factory.LazyFunction(_make_key)
    key_prefix = factory.LazyAttribute(lambda obj: obj._key_data[1])
    key_hash = factory.LazyAttribute(lambda obj: obj._key_data[2])

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        super()._after_postgeneration(instance, create, results)
        # Stash the raw key on the instance so tests can use it
        instance._raw_api_key = instance._key_data[0]

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        key_data = kwargs.pop('_key_data', None)
        instance = super()._create(model_class, *args, **kwargs)
        if key_data:
            instance._key_data = key_data
            instance._raw_api_key = key_data[0]
        return instance


class SpaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Space

    home = factory.SubFactory(HomeFactory)
    name = factory.Sequence(lambda n: f'Room {n}')
    is_public = False


class SensorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sensor
        exclude = ['_key_data']

    _key_data = factory.LazyFunction(_make_key)
    space = factory.SubFactory(SpaceFactory)
    name = factory.Sequence(lambda n: f'Sensor {n}')
    sensor_type = 'DHT22'
    key_prefix = factory.LazyAttribute(lambda obj: obj._key_data[1])
    key_hash = factory.LazyAttribute(lambda obj: obj._key_data[2])
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        key_data = kwargs.pop('_key_data', None)
        instance = super()._create(model_class, *args, **kwargs)
        if key_data:
            instance._raw_api_key = key_data[0]
        return instance


class SensorReadingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SensorReading

    sensor = factory.SubFactory(SensorFactory)
    data = factory.LazyFunction(lambda: {'temperature': 25.6, 'humidity': 48.2})
    recorded_at = factory.LazyFunction(timezone.now)

