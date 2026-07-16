from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Sensor, SensorReading


@shared_task
def detect_dead_sensors():
    """Check for sensors that haven't reported in the last 15 minutes."""
    threshold = timezone.now() - timedelta(minutes=15)
    active_sensors = Sensor.objects.filter(is_active=True)

    dead_sensors = []
    for sensor in active_sensors:
        last_reading = SensorReading.objects.filter(
            sensor=sensor
        ).order_by('-recorded_at').first()

        if last_reading and last_reading.recorded_at < threshold:
            dead_sensors.append(sensor.id)

    if dead_sensors:
        # TODO: Send notifications to owners
        pass

    return f"Checked {active_sensors.count()} sensors, {len(dead_sensors)} dead."


@shared_task
def cleanup_old_readings(days=90):
    """Delete raw readings older than the given number of days."""

    cutoff = timezone.now() - timedelta(days=days)
    deleted_count, _ = SensorReading.objects.filter(
        recorded_at__lt=cutoff
    ).delete()
    return f"Deleted {deleted_count} readings older than {days} days."

