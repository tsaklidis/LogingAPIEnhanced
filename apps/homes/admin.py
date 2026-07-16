from django.contrib import admin

from .models import Home, Space


@admin.register(Home)
class HomeAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'location', 'has_gateway_key', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'location']
    readonly_fields = ['key_prefix', 'key_hash']

    @admin.display(boolean=True, description='Gateway Key')
    def has_gateway_key(self, obj):
        return bool(obj.key_hash)


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'home', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name']

