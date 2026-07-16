from rest_framework import permissions

from .models import Sensor


class IsSensorOwner(permissions.BasePermission):
    """
    Allows access only if the sensor belongs to the requesting user.
    Works with views that pass sensor_pk or pk in URL kwargs.
    """

    def has_permission(self, request, view):
        sensor_pk = view.kwargs.get('sensor_pk') or view.kwargs.get('pk')
        if not sensor_pk:
            return False
        return Sensor.objects.filter(
            pk=sensor_pk,
            space__home__owner=request.user,
        ).exists()


class IsSensorPublic(permissions.BasePermission):
    """
    Allows access if the sensor belongs to a public space.
    No authentication required.
    """

    def has_permission(self, request, view):
        sensor_pk = view.kwargs.get('sensor_pk') or view.kwargs.get('pk')
        if not sensor_pk:
            return False
        return Sensor.objects.filter(
            pk=sensor_pk,
            space__is_public=True,
        ).exists()

