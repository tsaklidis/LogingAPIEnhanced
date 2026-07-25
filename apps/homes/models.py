import uuid

from django.conf import settings
from django.db import models


class Home(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='homes',
    )
    name = models.CharField(max_length=128)
    location = models.CharField(max_length=255, blank=True)
    key_prefix = models.CharField(
        max_length=16,
        db_index=True,
        blank=True,
        default='',
        help_text='Non-secret prefix of the gateway API key for fast DB lookup.',
    )
    key_hash = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text='SHA-256 hash of the full gateway API key.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'homes'
        indexes = [models.Index(fields=['owner'])]

    def __str__(self):
        return self.name

    @property
    def has_gateway_key(self):
        return bool(self.key_hash)



class Space(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    home = models.ForeignKey(Home, on_delete=models.CASCADE, related_name='spaces')
    name = models.CharField(max_length=128)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'spaces'

    def __str__(self):
        return f"{self.home.name} - {self.name}"
