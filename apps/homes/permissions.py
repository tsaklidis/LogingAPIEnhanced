from rest_framework import permissions


class IsHomeOwner(permissions.BasePermission):
    """Only allow the owner of a home to access it."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        if hasattr(obj, "home"):
            return obj.home.owner == request.user
        return False
