# layers/admin.py
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import LayerType, ProjectLayerGroup, ProjectLayer, ProjectLayerData, LayerPermission


@admin.register(LayerType)
class LayerTypeAdmin(admin.ModelAdmin):
    list_display = ('type_name', 'is_system', 'created_at')
    list_filter = ('is_system',)
    search_fields = ('type_name', 'description')
    fieldsets = (
        (None, {
            'fields': ('type_name', 'description', 'is_system')
        }),
        ('Style Options', {
            'fields': ('default_style', 'icon_type', 'icon_options')
        }),
    )


@admin.register(ProjectLayerGroup)
class ProjectLayerGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'display_order', 'is_visible_by_default')
    list_filter = ('is_visible_by_default', 'is_expanded_by_default', 'project')
    search_fields = ('name', 'project__name')
    ordering = ('project', 'display_order')


@admin.register(ProjectLayer)
class ProjectLayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_layer_group', 'layer_type', 'feature_count', 'is_visible_by_default')
    list_filter = ('layer_type', 'is_visible_by_default', 'project_layer_group__project')
    search_fields = ('name', 'description', 'project_layer_group__name')
    readonly_fields = ('feature_count', 'last_data_update', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('project_layer_group', 'layer_type', 'name', 'description', 'z_index')
        }),
        ('Visibility', {
            'fields': ('is_visible_by_default', 'min_zoom_visibility', 'max_zoom_visibility')
        }),
        ('Styling', {
            'fields': ('style', 'marker_type', 'marker_image_url', 'marker_options')
        }),
        ('Advanced Options', {
            'classes': ('collapse',),
            'fields': ('enable_clustering', 'clustering_options', 'enable_labels', 'label_options',
                       'data_source', 'attribution')
        }),
        ('Statistics', {
            'fields': ('feature_count', 'last_data_update', 'created_at', 'updated_at')
        }),
    )


@admin.register(ProjectLayerData)
class ProjectLayerDataAdmin(GISModelAdmin):
    list_display = ('feature_id', 'project_layer', 'geometry_type', 'created_at')
    list_filter = ('project_layer__name', 'created_at')
    search_fields = ('feature_id', 'project_layer__name')
    readonly_fields = ('created_at',)

    def geometry_type(self, obj):
        return obj.geometry.geom_type if obj.geometry else 'None'

    geometry_type.short_description = 'Geometry Type'


@admin.register(LayerPermission)
class LayerPermissionAdmin(admin.ModelAdmin):
    list_display = ('project_layer', 'client_project', 'can_view', 'can_edit', 'can_export')
    list_filter = ('can_view', 'can_edit', 'can_export')
    search_fields = ('project_layer__name', 'client_project__client__name')