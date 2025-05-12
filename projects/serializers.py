# projects/serializers.py
from rest_framework import serializers
from .models import Project
from django.contrib.auth import get_user_model

User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for project objects."""

    creator_username = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'description', 'is_public', 'is_active',
            'default_center_lat', 'default_center_lng', 'default_zoom_level',
            'map_controls', 'map_options', 'max_zoom', 'min_zoom',
            'created_at', 'updated_at', 'created_by_user', 'creator_username'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_creator_username(self, obj):
        if obj.created_by_user:
            return obj.created_by_user.username
        return None


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating project objects."""

    class Meta:
        model = Project
        fields = (
            'id',  # Add the id field to the serializer
            'name', 'description', 'is_public', 'is_active',
            'default_center_lat', 'default_center_lng', 'default_zoom_level',
            'map_controls', 'map_options', 'max_zoom', 'min_zoom',
        )
        read_only_fields = ('id',)  # Mark it as read-only