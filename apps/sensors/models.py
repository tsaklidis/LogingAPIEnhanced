import uuid

from django.db import models
from django.utils import timezone

from apps.homes.models import Space


class Sensor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name="sensors")
    name = models.CharField(max_length=128)
    sensor_type = models.CharField(max_length=64)  # "DHT22", "BME280", "BMP180"
    key_prefix = models.CharField(
        max_length=16,
        db_index=True,
        blank=True,
        default="",
        help_text="Non-secret prefix for fast DB lookup.",
    )
    key_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 hash of the full API key.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sensors"

    def __str__(self):
        return f"{self.name} ({self.sensor_type})"


class SensorReading(models.Model):
    """
    One row = one full data packet from a sensor.
    Uses PostgreSQL JSONField for flexible, schema-less payloads.

    Example data: {"temperature": 25.6, "humidity": 48.2, "battery_percentage": 35, "battery_voltage": 3.2}
    """

    id = models.BigAutoField(primary_key=True)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name="readings")
    data = models.JSONField()
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "sensor_readings"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["sensor", "-recorded_at"]),
        ]

    def __str__(self):
        return f"{self.sensor.name} @ {self.recorded_at}"
