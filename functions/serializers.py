# functions/serializers.py
from rest_framework import serializers
from .models import LayerFunction, ProjectLayerFunction, MapTool, ProjectTool


class LayerFunctionSerializer(serializers.ModelSerializer):
    """Serializer for layer function objects."""

    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')
    function_type_display = serializers.ReadOnlyField(source='get_function_type_display')

    class Meta:
        model = LayerFunction
        fields = (
            'id', 'name', 'description', 'function_type', 'function_type_display',
            'function_config', 'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')
        extra_kwargs = {
            'function_code': {'write_only': True}  # Don't expose code in regular responses
        }

    def create(self, validated_data):
        """Create a function with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class LayerFunctionDetailSerializer(LayerFunctionSerializer):
    """Extended serializer for layer function details including code."""

    class Meta(LayerFunctionSerializer.Meta):
        fields = LayerFunctionSerializer.Meta.fields + ('function_code',)


class ProjectLayerFunctionSerializer(serializers.ModelSerializer):
    """Serializer for project layer function associations."""

    function_name = serializers.ReadOnlyField(source='layer_function.name')
    function_type = serializers.ReadOnlyField(source='layer_function.function_type')
    layer_name = serializers.ReadOnlyField(source='project_layer.name')

    class Meta:
        model = ProjectLayerFunction
        fields = (
            'id', 'project_layer', 'layer_name', 'layer_function', 'function_name',
            'function_type', 'function_arguments', 'enabled', 'priority',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'function_name', 'layer_name')


class MapToolSerializer(serializers.ModelSerializer):
    """Serializer for map tool objects."""

    created_by_username = serializers.ReadOnlyField(source='created_by_user.username')
    tool_type_display = serializers.ReadOnlyField(source='get_tool_type_display')
    ui_position_display = serializers.ReadOnlyField(source='get_ui_position_display')

    class Meta:
        model = MapTool
        fields = (
            'id', 'name', 'description', 'tool_type', 'tool_type_display',
            'icon', 'default_options', 'ui_position', 'ui_position_display',
            'is_system', 'created_by_user', 'created_by_username',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by_username')
        extra_kwargs = {
            'tool_code': {'write_only': True}  # Don't expose code in regular responses
        }

    def create(self, validated_data):
        """Create a tool with the current user as creator."""
        user = self.context['request'].user
        validated_data['created_by_user'] = user
        return super().create(validated_data)


class MapToolDetailSerializer(MapToolSerializer):
    """Extended serializer for map tool details including code."""

    class Meta(MapToolSerializer.Meta):
        fields = MapToolSerializer.Meta.fields + ('tool_code',)


class ProjectToolSerializer(serializers.ModelSerializer):
    """Serializer for project tool associations."""

    tool_name = serializers.ReadOnlyField(source='tool.name')
    tool_type = serializers.ReadOnlyField(source='tool.tool_type')
    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = ProjectTool
        fields = (
            'id', 'project', 'project_name', 'tool', 'tool_name',
            'tool_type', 'is_enabled', 'display_order', 'tool_options',
            'custom_position', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'tool_name', 'project_name')