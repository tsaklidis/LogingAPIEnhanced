from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Sensor, SensorReading


class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ['id', 'space', 'name', 'sensor_type', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SensorCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ['id', 'name', 'sensor_type', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = ['id', 'data', 'recorded_at']
        read_only_fields = ['id', 'sensor']


def _validate_recorded_at(value):
    """Shared validation for recorded_at timestamps."""
    now = timezone.now()
    if value and value > now:
        raise serializers.ValidationError('recorded_at cannot be in the future.')
    if value and value < now - timedelta(days=30):
        raise serializers.ValidationError('recorded_at cannot be more than 30 days in the past.')
    return value


def _validate_sensor_data(value):
    """Shared validation for sensor data payloads."""
    if not isinstance(value, dict):
        raise serializers.ValidationError('data must be a JSON object.')
    if not value:
        raise serializers.ValidationError('data cannot be empty.')
    return value


class IngestSerializer(serializers.Serializer):
    """Serializer for single sensor data ingestion (per-sensor key auth)."""
    data = serializers.JSONField()
    recorded_at = serializers.DateTimeField(required=False)

    def validate_recorded_at(self, value):
        return _validate_recorded_at(value)

    def validate_data(self, value):
        return _validate_sensor_data(value)


class BulkIngestSerializer(serializers.ListSerializer):
    """Serializer for bulk sensor data ingestion (per-sensor key auth)."""
    child = IngestSerializer()

    def validate(self, data):
        if len(data) > 1000:
            raise serializers.ValidationError('Maximum 1000 readings per bulk request.')
        return data


# --- Gateway ingestion serializers (home-level key) ---


class GatewayIngestItemSerializer(serializers.Serializer):
    """A single reading in a gateway ingestion payload — requires sensor_id."""
    sensor_id = serializers.UUIDField()
    data = serializers.JSONField()
    recorded_at = serializers.DateTimeField(required=False)

    def validate_recorded_at(self, value):
        return _validate_recorded_at(value)

    def validate_data(self, value):
        return _validate_sensor_data(value)


class GatewayIngestSerializer(serializers.Serializer):
    """
    Gateway ingestion: a list of readings, each tagged with a sensor_id.
    Used by central gateway devices that collect data from multiple sensors.
    """
    readings = GatewayIngestItemSerializer(many=True)

    def validate_readings(self, value):
        if not value:
            raise serializers.ValidationError('readings list cannot be empty.')
        if len(value) > 1000:
            raise serializers.ValidationError('Maximum 1000 readings per request.')
        return value


