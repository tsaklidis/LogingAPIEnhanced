from rest_framework import permissions


class IsActiveUser(permissions.BasePermission):
    """
    Rejects inactive users even if they hold a valid token.

    Defense-in-depth: if a user is deactivated after token issuance,
    this blocks access immediately without waiting for token expiry.
    """

    message = "Your account is inactive. Please contact an administrator."

    def has_permission(self, request, view):
        return request.user and request.user.is_active


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level permission: only the owner can modify, anyone can read."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return False
