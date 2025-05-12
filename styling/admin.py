# styling/admin.py
from django.contrib import admin
from .models import MarkerLibrary, PopupTemplate, StyleLibrary, ColorPalette


@admin.register(MarkerLibrary)
class MarkerLibraryAdmin(admin.ModelAdmin):
    """Admin configuration for marker library model."""

    list_display = ('name', 'icon_type', 'category', 'is_system', 'created_by_user', 'created_at')
    list_filter = ('icon_type', 'is_system', 'category')
    search_fields = ('name', 'description', 'tags')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_system')
        }),
        ('Icon Definition', {
            'fields': ('icon_url', 'icon_type', 'icon_data')
        }),
        ('Style Options', {
            'fields': ('default_options', 'default_size', 'default_anchor', 'default_color')
        }),
        ('Categorization', {
            'fields': ('tags', 'category')
        }),
        ('Metadata', {
            'fields': ('created_by_user', 'created_at', 'updated_at')
        }),
    )


@admin.register(PopupTemplate)
class PopupTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for popup template model."""

    list_display = ('name', 'max_width', 'max_height', 'is_system', 'created_by_user', 'created_at')
    list_filter = ('is_system', 'include_zoom_to_feature')
    search_fields = ('name', 'description', 'html_template')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_system')
        }),
        ('Template Content', {
            'fields': ('html_template', 'field_mappings', 'css_styles')
        }),
        ('Display Settings', {
            'fields': ('max_width', 'max_height', 'include_zoom_to_feature')
        }),
        ('Metadata', {
            'fields': ('created_by_user', 'created_at', 'updated_at')
        }),
    )


@admin.register(StyleLibrary)
class StyleLibraryAdmin(admin.ModelAdmin):
    """Admin configuration for style library model."""

    list_display = ('name', 'style_type', 'is_system', 'created_by_user', 'created_at')
    list_filter = ('style_type', 'is_system')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'style_type', 'is_system')
        }),
        ('Style Definition', {
            'fields': ('style_definition', 'preview_image')
        }),
        ('Metadata', {
            'fields': ('created_by_user', 'created_at', 'updated_at')
        }),
    )


@admin.register(ColorPalette)
class ColorPaletteAdmin(admin.ModelAdmin):
    """Admin configuration for color palette model."""

    list_display = ('name', 'palette_type', 'is_system', 'created_by_user', 'created_at')
    list_filter = ('palette_type', 'is_system')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'palette_type', 'is_system')
        }),
        ('Colors', {
            'fields': ('colors',)
        }),
        ('Metadata', {
            'fields': ('created_by_user', 'created_at', 'updated_at')
        }),
    )