# basemaps/admin.py
from django.contrib import admin
from .models import Basemap, ProjectBasemap


@admin.register(Basemap)
class BasemapAdmin(admin.ModelAdmin):
    """Admin configuration for the Basemap model."""

    list_display = ('name', 'provider', 'is_system', 'created_by_user', 'created_at')
    list_filter = ('provider', 'is_system')
    search_fields = ('name', 'description', 'url_template')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_system')
        }),
        ('Provider Configuration', {
            'fields': ('provider', 'url_template', 'attribution', 'api_key')
        }),
        ('Options', {
            'fields': ('options', 'min_zoom', 'max_zoom', 'preview_image')
        }),
        ('Metadata', {
            'fields': ('created_by_user', 'created_at', 'updated_at')
        })
    )


@admin.register(ProjectBasemap)
class ProjectBasemapAdmin(admin.ModelAdmin):
    """Admin configuration for the ProjectBasemap model."""

    list_display = ('project', 'basemap', 'is_default', 'display_order', 'created_at')
    list_filter = ('is_default', 'project', 'basemap')
    search_fields = ('project__name', 'basemap__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('project', 'basemap')
        }),
        ('Display Options', {
            'fields': ('is_default', 'display_order', 'custom_options')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        })
    )