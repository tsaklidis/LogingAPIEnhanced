from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "is_active", "is_staff", "date_joined"]
    list_filter = ["is_active", "is_staff", "is_superuser", "date_joined"]
    actions = ["approve_users", "deactivate_users"]

    @admin.action(description="Approve selected users (set active)")
    def approve_users(self, request, queryset):
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(request, f"{count} user(s) approved and activated.")

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        count = queryset.filter(is_active=True, is_superuser=False).update(is_active=False)
        self.message_user(request, f"{count} user(s) deactivated.")
