# projects/admin.py
from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin configuration for Project model."""

    list_display = ('name', 'is_public', 'is_active', 'created_by_user', 'created_at')
    list_filter = ('is_public', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'created_by_user__username')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_public', 'is_active', 'created_by_user')
        }),
        ('Map Settings', {
            'fields': ('default_center_lat', 'default_center_lng', 'default_zoom_level',
                       'min_zoom', 'max_zoom')
        }),
        ('Advanced Settings', {
            'classes': ('collapse',),
            'fields': ('map_controls', 'map_options')
        }),
        ('Important dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )