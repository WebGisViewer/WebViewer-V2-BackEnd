# functions/admin.py
from django.contrib import admin
from .models import LayerFunction, ProjectLayerFunction, MapTool, ProjectTool


@admin.register(LayerFunction)
class LayerFunctionAdmin(admin.ModelAdmin):
    """Admin configuration for the LayerFunction model."""

    list_display = ('name', 'function_type', 'is_system', 'created_by_user', 'created_at')
    list_filter = ('function_type', 'is_system')
    search_fields = ('name', 'description', 'function_code')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_system')
        }),
        ('Function Configuration', {
            'fields': ('function_type', 'function_config')
        }),
        ('Implementation', {
            'fields': ('function_code',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by_user', 'created_at', 'updated_at')
        })
    )


@admin.register(ProjectLayerFunction)
class ProjectLayerFunctionAdmin(admin.ModelAdmin):
    """Admin configuration for the ProjectLayerFunction model."""

    list_display = ('project_layer', 'layer_function', 'enabled', 'priority', 'created_at')
    list_filter = ('enabled', 'project_layer__project_layer_group__project', 'layer_function')
    search_fields = ('project_layer__name', 'layer_function__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('project_layer', 'layer_function')
        }),
        ('Configuration', {
            'fields': ('enabled', 'priority', 'function_arguments')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(MapTool)
class MapToolAdmin(admin.ModelAdmin):
    """Admin configuration for the MapTool model."""

    list_display = ('name', 'tool_type', 'ui_position', 'is_system', 'created_by_user', 'created_at')
    list_filter = ('tool_type', 'ui_position', 'is_system')
    search_fields = ('name', 'description', 'tool_code')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_system')
        }),
        ('Tool Configuration', {
            'fields': ('tool_type', 'icon', 'default_options', 'ui_position')
        }),
        ('Implementation', {
            'fields': ('tool_code',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by_user', 'created_at', 'updated_at')
        })
    )


@admin.register(ProjectTool)
class ProjectToolAdmin(admin.ModelAdmin):
    """Admin configuration for the ProjectTool model."""

    list_display = ('project', 'tool', 'is_enabled', 'display_order', 'created_at')
    list_filter = ('is_enabled', 'project', 'tool')
    search_fields = ('project__name', 'tool__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('project', 'tool')
        }),
        ('Display Options', {
            'fields': ('is_enabled', 'display_order', 'custom_position', 'tool_options')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        })
    )