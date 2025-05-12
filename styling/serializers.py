# styling/serializers.py
from rest_framework import serializers
from .models import MarkerLibrary, PopupTemplate, StyleLibrary, ColorPalette
from django.core.files.base import ContentFile
import base64
import uuid


class MarkerLibrarySerializer(serializers.ModelSerializer):
    """Serializer for marker library objects."""

    icon_data_base64 = serializers.SerializerMethodField(read_only=True)
    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')

    class Meta:
        model = MarkerLibrary
        fields = (
            'id', 'name', 'description', 'icon_url', 'icon_type',
            'default_options', 'default_size', 'default_anchor', 'default_color',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at', 'tags', 'category', 'icon_data_base64'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')

    def get_icon_data_base64(self, obj):
        """Convert binary icon data to base64 for frontend display."""
        if obj.icon_data:
            return base64.b64encode(obj.icon_data).decode('utf-8')
        return None

    def create(self, validated_data):
        """Create a marker with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class PopupTemplateSerializer(serializers.ModelSerializer):
    """Serializer for popup template objects."""

    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')

    class Meta:
        model = PopupTemplate
        fields = (
            'id', 'name', 'description', 'html_template', 'field_mappings',
            'css_styles', 'max_width', 'max_height', 'include_zoom_to_feature',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')

    def create(self, validated_data):
        """Create a template with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class StyleLibrarySerializer(serializers.ModelSerializer):
    """Serializer for style library objects."""

    preview_image_base64 = serializers.SerializerMethodField(read_only=True)
    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')

    class Meta:
        model = StyleLibrary
        fields = (
            'id', 'name', 'description', 'style_definition', 'style_type',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at', 'preview_image_base64'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')

    def get_preview_image_base64(self, obj):
        """Convert binary preview image to base64 for frontend display."""
        if obj.preview_image:
            return base64.b64encode(obj.preview_image).decode('utf-8')
        return None

    def create(self, validated_data):
        """Create a style with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class ColorPaletteSerializer(serializers.ModelSerializer):
    """Serializer for color palette objects."""

    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')

    class Meta:
        model = ColorPalette
        fields = (
            'id', 'name', 'description', 'colors', 'palette_type',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')

    def create(self, validated_data):
        """Create a palette with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)