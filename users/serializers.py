from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import AuditLog

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user objects."""

    client_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name', 'is_admin',
                  'client', 'client_name', 'created_at', 'updated_at', 'last_login')
        read_only_fields = ('id', 'created_at', 'updated_at', 'last_login')

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.name
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user objects."""

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name', 'password',
                  'password_confirm', 'is_admin', 'client')
        read_only_fields = ('id',)

    def validate(self, attrs):
        """Validate that the passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        """Create and return a new user."""
        # Remove password_confirm field as it's not needed for user creation
        validated_data.pop('password_confirm')

        # Create user with create_user method to properly hash password
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user objects."""

    class Meta:
        model = User
        fields = ('email', 'full_name', 'is_admin')


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        """Validate the passwords."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs."""

    username = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ('id', 'username', 'action', 'action_details', 'occurred_at', 'ip_address')
        read_only_fields = fields

    def get_username(self, obj):
        """Get the username or 'Unknown' if user is None."""
        return obj.user.username if obj.user else 'Unknown'