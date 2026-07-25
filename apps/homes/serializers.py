from rest_framework import serializers

from .models import Home, Space


class SpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Space
        fields = ["id", "home", "name", "is_public", "created_at", "updated_at"]
        read_only_fields = ["id", "home", "created_at", "updated_at"]


class HomeSerializer(serializers.ModelSerializer):
    spaces = SpaceSerializer(many=True, read_only=True)

    class Meta:
        model = Home
        fields = ["id", "name", "location", "spaces", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class HomeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Home
        fields = ["id", "name", "location", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
