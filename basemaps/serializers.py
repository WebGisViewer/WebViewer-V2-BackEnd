# basemaps/serializers.py
from rest_framework import serializers
from .models import Basemap, ProjectBasemap
import base64


class BasemapSerializer(serializers.ModelSerializer):
    """Serializer for basemap objects."""

    preview_image_base64 = serializers.SerializerMethodField(read_only=True)
    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')
    provider_display = serializers.ReadOnlyField(source='get_provider_display')

    class Meta:
        model = Basemap
        fields = (
            'id', 'name', 'description', 'provider', 'provider_display',
            'url_template', 'options', 'attribution', 'min_zoom', 'max_zoom',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at', 'preview_image_base64'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')
        extra_kwargs = {
            'api_key': {'write_only': True}  # Never expose API keys in responses
        }

    def get_preview_image_base64(self, obj):
        """Convert binary preview image to base64 for frontend display."""
        if obj.preview_image:
            return base64.b64encode(obj.preview_image).decode('utf-8')
        return None

    def create(self, validated_data):
        """Create a basemap with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class ProjectBasemapSerializer(serializers.ModelSerializer):
    """Serializer for project basemap associations."""

    basemap_name = serializers.ReadOnlyField(source='basemap.name')
    basemap_provider = serializers.ReadOnlyField(source='basemap.provider')
    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = ProjectBasemap
        fields = (
            'id', 'project', 'project_name', 'basemap', 'basemap_name',
            'basemap_provider', 'is_default', 'display_order',
            'custom_options', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'project_name', 'basemap_name')


class BasemapDetailSerializer(BasemapSerializer):
    """Extended serializer for basemap details including projects."""

    projects = serializers.SerializerMethodField()

    class Meta(BasemapSerializer.Meta):
        fields = BasemapSerializer.Meta.fields + ('projects',)

    def get_projects(self, obj):
        """List projects using this basemap."""
        project_basemaps = obj.project_instances.all()
        return [
            {
                'id': pb.project.id,
                'name': pb.project.name,
                'is_default': pb.is_default,
                'display_order': pb.display_order
            }
            for pb in project_basemaps
        ]