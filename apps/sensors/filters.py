import django_filters

from .models import SensorReading


class SensorReadingFilter(django_filters.FilterSet):
    from_date = django_filters.IsoDateTimeFilter(field_name="recorded_at", lookup_expr="gte")
    to_date = django_filters.IsoDateTimeFilter(field_name="recorded_at", lookup_expr="lte")

    class Meta:
        model = SensorReading
        fields = ["from_date", "to_date"]
