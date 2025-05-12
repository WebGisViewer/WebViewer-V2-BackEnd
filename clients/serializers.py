# clients/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, ClientProject

User = get_user_model()


class ClientSerializer(serializers.ModelSerializer):
    """Serializer for client objects."""

    class Meta:
        model = Client
        fields = ('id', 'name', 'contact_email', 'contact_phone', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class ClientDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for client objects with user count."""

    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ('id', 'name', 'contact_email', 'contact_phone',
                  'is_active', 'created_at', 'updated_at', 'user_count')
        read_only_fields = ('id', 'created_at', 'updated_at', 'user_count')

    def get_user_count(self, obj):
        return obj.users.count()


class ClientUserSerializer(serializers.ModelSerializer):
    """Serializer for users associated with a client."""

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name', 'is_active', 'last_login')
        read_only_fields = fields


class ClientProjectSerializer(serializers.ModelSerializer):
    """Serializer for client projects."""

    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = ClientProject
        fields = ('id', 'client', 'project', 'project_name', 'unique_link',
                  'is_active', 'created_at', 'expires_at', 'last_accessed')
        read_only_fields = ('id', 'created_at', 'last_accessed')