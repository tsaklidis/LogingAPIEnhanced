import factory
from django.utils import timezone

from apps.accounts.models import User
from apps.common.apikey import generate_key
from apps.homes.models import Home, Space
from apps.sensors.models import Sensor, SensorReading


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class HomeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Home

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Home {n}")
    location = factory.Faker("address")
    key_prefix = ""
    key_hash = ""


class HomeWithGatewayFactory(HomeFactory):
    """Home with a pre-generated gateway API key."""

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        raw_key, prefix, key_hash = generate_key()
        kwargs["key_prefix"] = prefix
        kwargs["key_hash"] = key_hash
        instance = super()._create(model_class, *args, **kwargs)
        instance._raw_api_key = raw_key
        return instance


class SpaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Space

    home = factory.SubFactory(HomeFactory)
    name = factory.Sequence(lambda n: f"Room {n}")
    is_public = False


class SensorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sensor

    space = factory.SubFactory(SpaceFactory)
    name = factory.Sequence(lambda n: f"Sensor {n}")
    sensor_type = "DHT22"
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        raw_key, prefix, key_hash = generate_key()
        kwargs["key_prefix"] = prefix
        kwargs["key_hash"] = key_hash
        instance = super()._create(model_class, *args, **kwargs)
        instance._raw_api_key = raw_key
        return instance


class SensorReadingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SensorReading

    sensor = factory.SubFactory(SensorFactory)
    data = factory.LazyFunction(lambda: {"temperature": 25.6, "humidity": 48.2})
    recorded_at = factory.LazyFunction(timezone.now)
