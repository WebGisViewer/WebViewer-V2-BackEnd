# styling/models.py
from django.db import models
from django.utils import timezone
import uuid


class MarkerLibrary(models.Model):
    """
    Repository of custom map markers.

    This model stores marker icons that can be used on map layers,
    supporting different formats like images, SVGs, or font icons.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Icon specifications
    icon_url = models.CharField(max_length=255, blank=True, null=True)
    icon_type = models.CharField(
        max_length=50,
        default='image',
        choices=[
            ('image', 'Image'),
            ('svg', 'SVG'),
            ('font', 'Font Icon'),
            ('emoji', 'Emoji'),
            ('circle', 'Circle'),
            ('custom', 'Custom HTML'),
        ]
    )
    icon_data = models.BinaryField(null=True, blank=True)  # For storing SVGs or other marker data

    # Icon styling options
    default_options = models.JSONField(default=dict, blank=True)
    default_size = models.IntegerField(default=24, help_text="Size in pixels")
    default_anchor = models.CharField(max_length=50, default="center",
                                      help_text="Anchor position (e.g., 'center', 'bottom')")
    default_color = models.CharField(max_length=30, blank=True, null=True, help_text="Default color (e.g., '#FF5500')")

    # Metadata
    is_system = models.BooleanField(default=False)
    created_by_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Tagging and categorization
    tags = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated tags for searching")
    category = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'marker_library_wiroi_online'
        verbose_name = 'Marker'
        verbose_name_plural = 'Marker Library'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class PopupTemplate(models.Model):
    """
    HTML templates for feature information popups.

    Templates can include field mappings to automatically
    display feature properties in a structured format.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Template content and mapping
    html_template = models.TextField(
        help_text="HTML template with placeholders like {{field_name}}"
    )
    field_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON mapping of template placeholders to feature properties"
    )
    css_styles = models.TextField(
        blank=True,
        null=True,
        help_text="Optional CSS styles for the popup"
    )

    # Display settings
    max_width = models.IntegerField(
        default=300,
        help_text="Maximum width of the popup in pixels"
    )
    max_height = models.IntegerField(
        default=400,
        help_text="Maximum height of the popup in pixels"
    )

    # Dynamic behavior settings
    include_zoom_to_feature = models.BooleanField(
        default=True,
        help_text="Add a button to zoom to the feature"
    )

    # Metadata
    is_system = models.BooleanField(default=False)
    created_by_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'popup_templates_wiroi_online'
        verbose_name = 'Popup Template'
        verbose_name_plural = 'Popup Templates'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class StyleLibrary(models.Model):
    """
    Collection of reusable styles for map features.

    Styles can be applied to layers based on feature properties
    or other conditions.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Style definition
    style_definition = models.JSONField(
        default=dict,
        help_text="JSON style definition following Leaflet/Mapbox standards"
    )

    # Style type
    style_type = models.CharField(
        max_length=50,
        choices=[
            ('point', 'Point Style'),
            ('line', 'Line Style'),
            ('polygon', 'Polygon Style'),
            ('label', 'Label Style'),
            ('universal', 'Universal Style'),
        ],
        default='universal'
    )

    # Metadata
    is_system = models.BooleanField(default=False)
    created_by_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Preview image
    preview_image = models.BinaryField(null=True, blank=True)

    class Meta:
        db_table = 'style_library_wiroi_online'
        verbose_name = 'Style'
        verbose_name_plural = 'Style Library'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ColorPalette(models.Model):
    """
    Predefined color palettes for map visualization.

    Palettes can be used for thematic mapping, choropleth maps,
    or general styling consistency.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Color definitions
    colors = models.JSONField(
        default=list,
        help_text="List of colors in the palette"
    )

    # Palette type
    palette_type = models.CharField(
        max_length=50,
        choices=[
            ('sequential', 'Sequential'),
            ('diverging', 'Diverging'),
            ('qualitative', 'Qualitative'),
            ('custom', 'Custom'),
        ],
        default='custom'
    )

    # Metadata
    is_system = models.BooleanField(default=False)
    created_by_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'color_palettes_wiroi_online'
        verbose_name = 'Color Palette'
        verbose_name_plural = 'Color Palettes'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)