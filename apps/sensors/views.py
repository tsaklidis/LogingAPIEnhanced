from django.core.cache import cache
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.apikey import generate_key
from apps.homes.models import Home, Space

from .authentication import GatewayKeyAuthentication, SensorKeyAuthentication
from .filters import SensorReadingFilter
from .models import Sensor, SensorReading
from .permissions import IsSensorOwner, IsSensorPublic
from .serializers import (
    BulkIngestSerializer,
    GatewayIngestSerializer,
    IngestSerializer,
    PublicSensorSerializer,
    SensorCreateSerializer,
    SensorReadingSerializer,
    SensorSerializer,
)


class SensorListCreateView(generics.ListCreateAPIView):
    """List sensors for a space or create a new one."""
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'management'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SensorCreateSerializer
        return SensorSerializer

    def get_queryset(self):
        return Sensor.objects.filter(
            space__home__owner=self.request.user,
            space_id=self.kwargs['space_pk'],
        )

    def perform_create(self, serializer):
        space = Space.objects.get(
            pk=self.kwargs['space_pk'],
            home__owner=self.request.user,
        )
        raw_key, prefix, key_hash = generate_key()
        serializer.save(space=space, key_prefix=prefix, key_hash=key_hash)
        # Attach raw key to serializer so the response includes it (shown once)
        serializer._raw_api_key = raw_key

    def create(self, request, *args, **kwargs):
        """Override to include the raw API key in the response (shown only once)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        data = serializer.data
        data['api_key'] = serializer._raw_api_key
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)


class SensorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a sensor."""
    serializer_class = SensorSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'management'
    lookup_field = 'pk'

    def get_queryset(self):
        return Sensor.objects.filter(space__home__owner=self.request.user)


class SensorRotateKeyView(APIView):
    """Rotate a sensor's API key."""
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'management'

    def post(self, request, pk):
        try:
            sensor = Sensor.objects.get(pk=pk, space__home__owner=request.user)
        except Sensor.DoesNotExist:
            return Response(
                {'detail': 'Sensor not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        raw_key, prefix, key_hash = generate_key()
        sensor.key_prefix = prefix
        sensor.key_hash = key_hash
        sensor.save(update_fields=['key_prefix', 'key_hash', 'updated_at'])
        return Response({'api_key': raw_key}, status=status.HTTP_200_OK)


class IngestView(APIView):
    """Ingest a single sensor reading. Authenticated via X-Sensor-Key only."""
    authentication_classes = [SensorKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'ingestion'

    def post(self, request):
        sensor = request.auth

        serializer = IngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reading = SensorReading.objects.create(
            sensor=sensor,
            data=serializer.validated_data['data'],
            recorded_at=serializer.validated_data.get('recorded_at', timezone.now()),
        )

        # Cache latest reading
        cache.set(
            f"sensor:{sensor.id}:latest",
            SensorReadingSerializer(reading).data,
        )

        return Response(
            {'id': reading.id, 'recorded_at': reading.recorded_at},
            status=status.HTTP_201_CREATED,
        )


class BulkIngestView(APIView):
    """Ingest multiple sensor readings at once. Authenticated via X-Sensor-Key only."""
    authentication_classes = [SensorKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'ingestion'

    def post(self, request):
        sensor = request.auth

        serializer = BulkIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        readings = [
            SensorReading(
                sensor=sensor,
                data=item['data'],
                recorded_at=item.get('recorded_at', now),
            )
            for item in serializer.validated_data
        ]

        SensorReading.objects.bulk_create(readings)

        # Cache the latest reading (by timestamp)
        if readings:
            latest = max(readings, key=lambda r: r.recorded_at)
            cache.set(
                f"sensor:{sensor.id}:latest",
                SensorReadingSerializer(latest).data,
            )

        return Response(
            {'count': len(readings)},
            status=status.HTTP_201_CREATED,
        )


class SensorReadingListView(generics.ListAPIView):
    """List readings for a sensor (owner-scoped)."""
    serializer_class = SensorReadingSerializer
    permission_classes = [permissions.IsAuthenticated, IsSensorOwner]
    filterset_class = SensorReadingFilter
    ordering_fields = ['recorded_at']
    ordering = ['-recorded_at']
    throttle_scope = 'readings'

    def get_queryset(self):
        return SensorReading.objects.filter(
            sensor_id=self.kwargs['sensor_pk'],
        )


class SensorReadingLatestView(APIView):
    """Get the latest reading for a sensor (served from cache)."""
    permission_classes = [permissions.IsAuthenticated, IsSensorOwner]
    throttle_scope = 'readings'

    def get(self, request, sensor_pk):

        cached = cache.get(f"sensor:{sensor_pk}:latest")
        if cached:
            return Response(cached)

        reading = SensorReading.objects.filter(sensor_id=sensor_pk).first()
        if not reading:
            return Response(
                {'detail': 'No readings found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = SensorReadingSerializer(reading).data
        cache.set(f"sensor:{sensor_pk}:latest", data)
        return Response(data)


class PublicSensorReadingListView(generics.ListAPIView):
    """List readings for a public sensor (no auth required)."""
    serializer_class = SensorReadingSerializer
    permission_classes = [IsSensorPublic]
    authentication_classes = []
    filterset_class = SensorReadingFilter
    ordering_fields = ['recorded_at']
    ordering = ['-recorded_at']

    def get_queryset(self):
        return SensorReading.objects.filter(
            sensor_id=self.kwargs['sensor_pk'],
        )


class PublicSensorReadingLatestView(APIView):
    """Get the latest reading for a public sensor."""
    permission_classes = [IsSensorPublic]
    authentication_classes = []

    def get(self, request, sensor_pk):

        cached = cache.get(f"sensor:{sensor_pk}:latest")
        if cached:
            return Response(cached)

        reading = SensorReading.objects.filter(sensor_id=sensor_pk).first()
        if not reading:
            return Response(
                {'detail': 'No readings found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = SensorReadingSerializer(reading).data
        cache.set(f"sensor:{sensor_pk}:latest", data)
        return Response(data)


class PublicSensorListView(generics.ListAPIView):
    """List all sensors in public spaces (no auth required)."""
    serializer_class = PublicSensorSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    pagination_class = None

    def get_queryset(self):
        return Sensor.objects.filter(
            space__is_public=True,
            is_active=True,
        ).select_related('space', 'space__home')


# --- Gateway ingestion (home-level key) ---


class GatewayIngestView(APIView):
    """
    Ingest readings from multiple sensors in a single request.
    Authenticated via X-Gateway-Key only.
    """
    authentication_classes = [GatewayKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'ingestion'

    def post(self, request):
        home = request.auth

        serializer = GatewayIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data['readings']

        # Single pass: collect unique sensor IDs
        sensor_ids = {item['sensor_id'] for item in items}

        # One DB query: fetch all referenced sensors that belong to this home
        home_sensors = Sensor.objects.filter(
            id__in=sensor_ids,
            space__home=home,
            is_active=True,
        ).in_bulk(field_name='id')

        # Validate all sensor IDs are valid
        invalid_ids = sensor_ids - set(home_sensors.keys())
        if invalid_ids:
            return Response(
                {
                    'detail': 'Some sensor IDs are invalid, inactive, or do not belong to this home.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Single pass: build reading objects and track latest per sensor
        readings = []
        latest_per_sensor = {}
        now = timezone.now()

        for item in items:
            recorded_at = item.get('recorded_at', now)
            sid = item['sensor_id']
            reading = SensorReading(
                sensor=home_sensors[sid],
                data=item['data'],
                recorded_at=recorded_at,
            )
            readings.append(reading)
            # Track latest reading per sensor (by timestamp)
            if sid not in latest_per_sensor or recorded_at > latest_per_sensor[sid].recorded_at:
                latest_per_sensor[sid] = reading

        # One DB call: bulk insert all readings
        SensorReading.objects.bulk_create(readings)

        # One Redis call: update cache for all affected sensors
        cache.set_many({
            f"sensor:{sid}:latest": SensorReadingSerializer(reading).data
            for sid, reading in latest_per_sensor.items()
        })

        return Response(
            {
                'count': len(readings),
                'sensors': len(latest_per_sensor),
            },
            status=status.HTTP_201_CREATED,
        )


class HomeGatewayKeyView(APIView):
    """Generate or rotate the gateway API key for a home."""
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'management'

    def post(self, request, pk):
        try:
            home = Home.objects.get(pk=pk, owner=request.user)
        except Home.DoesNotExist:
            return Response(
                {'detail': 'Home not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        raw_key, prefix, key_hash = generate_key()
        home.key_prefix = prefix
        home.key_hash = key_hash
        home.save(update_fields=['key_prefix', 'key_hash', 'updated_at'])
        return Response({'api_key': raw_key}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        """Revoke the gateway key."""
        try:
            home = Home.objects.get(pk=pk, owner=request.user)
        except Home.DoesNotExist:
            return Response(
                {'detail': 'Home not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        home.key_prefix = ''
        home.key_hash = ''
        home.save(update_fields=['key_prefix', 'key_hash', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

