from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.common.apikey import parse_prefix, verify_key
from apps.homes.models import Home

from .models import Sensor


class SensorKeyAuthentication(BaseAuthentication):
    """
    Single-sensor auth: IoT devices send X-Sensor-Key: <prefix>.<secret>

    Lookup by prefix (fast, indexed), then verify the full key hash
    using constant-time comparison to prevent timing attacks.
    """

    def authenticate(self, request):
        raw_key = request.headers.get("X-Sensor-Key")
        if not raw_key:
            return None

        prefix = parse_prefix(raw_key)
        if not prefix:
            raise AuthenticationFailed("Invalid sensor key format")

        try:
            sensor = Sensor.objects.select_related("space__home__owner").get(key_prefix=prefix, is_active=True)
        except Sensor.DoesNotExist:
            raise AuthenticationFailed("Invalid or inactive sensor key") from None

        if not verify_key(raw_key, sensor.key_hash):
            raise AuthenticationFailed("Invalid or inactive sensor key")

        return (sensor.space.home.owner, sensor)

    def authenticate_header(self, request):
        return "X-Sensor-Key"


class GatewayKeyAuthentication(BaseAuthentication):
    """
    Home-level gateway auth: a central device sends X-Gateway-Key: <prefix>.<secret>

    Lookup by prefix (fast, indexed), then verify the full key hash
    using constant-time comparison to prevent timing attacks.
    """

    def authenticate(self, request):
        raw_key = request.headers.get("X-Gateway-Key")
        if not raw_key:
            return None

        prefix = parse_prefix(raw_key)
        if not prefix:
            raise AuthenticationFailed("Invalid gateway key format")

        try:
            home = Home.objects.select_related("owner").get(key_prefix=prefix)
        except Home.DoesNotExist:
            raise AuthenticationFailed("Invalid gateway key") from None

        if not home.key_hash or not verify_key(raw_key, home.key_hash):
            raise AuthenticationFailed("Invalid gateway key")

        return (home.owner, home)

    def authenticate_header(self, request):
        return "X-Gateway-Key"
