from django.contrib import admin

from .models import Sensor, SensorReading


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ['name', 'sensor_type', 'space', 'is_active', 'key_prefix', 'created_at']
    list_filter = ['sensor_type', 'is_active', 'created_at']
    search_fields = ['name', 'sensor_type']
    readonly_fields = ['key_prefix', 'key_hash']


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ['sensor', 'recorded_at']
    list_filter = ['sensor', 'recorded_at']
    date_hierarchy = 'recorded_at'

