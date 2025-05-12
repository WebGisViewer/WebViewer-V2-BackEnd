# basemaps/models.py
from django.db import models
from django.utils import timezone


class Basemap(models.Model):
    """
    Background map providers and tile sources.

    Basemaps can be standard providers like Google Maps, OpenStreetMap,
    or custom tile servers specified by URL templates.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Provider information
    provider = models.CharField(
        max_length=100,
        choices=[
            ('google', 'Google Maps'),
            ('google_satellite', 'Google Satellite'),
            ('openstreetmap', 'OpenStreetMap'),
            ('bing', 'Bing Maps'),
            ('esri', 'ESRI'),
            ('mapbox', 'Mapbox'),
            ('carto', 'Carto'),
            ('stamen', 'Stamen'),
            ('custom', 'Custom Tiles'),
            ('wms', 'WMS Service'),
            ('arcgis', 'ArcGIS Online'),
            ('blank', 'Blank Background')
        ],
        default='openstreetmap'
    )

    # URL template for tiles
    url_template = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL template with {x}, {y}, {z} placeholders for tile coordinates"
    )

    # API key or access token (encrypted in database)
    api_key = models.CharField(max_length=255, blank=True, null=True)

    # Additional options
    options = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional options for the tile layer (e.g., subdomains, min/max zoom)"
    )

    # Attribution required by the provider
    attribution = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Attribution text required by the map provider"
    )

    # Preview image
    preview_image = models.BinaryField(null=True, blank=True)

    # Visibility settings
    min_zoom = models.IntegerField(default=0)
    max_zoom = models.IntegerField(default=19)

    # Metadata
    is_system = models.BooleanField(default=False)
    created_by_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'basemaps_wiroi_online'
        verbose_name = 'Basemap'
        verbose_name_plural = 'Basemaps'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ProjectBasemap(models.Model):
    """
    Basemaps configured for a specific project.

    This junction table defines which basemaps are available in a project,
    their order, and which one is selected by default.
    """
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='project_basemaps')
    basemap = models.ForeignKey(Basemap, on_delete=models.CASCADE, related_name='project_instances')

    # Configuration
    is_default = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)

    # Custom options that override the basemap defaults for this project
    custom_options = models.JSONField(
        default=dict,
        blank=True,
        help_text="Project-specific options that override the basemap defaults"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_basemaps_wiroi_online'
        verbose_name = 'Project Basemap'
        verbose_name_plural = 'Project Basemaps'
        ordering = ['project', 'display_order']
        unique_together = ('project', 'basemap')

    def __str__(self):
        return f"{self.project.name} - {self.basemap.name}"

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()

        # If this basemap is marked as default, make sure no other basemap
        # for this project is marked as default
        if self.is_default:
            ProjectBasemap.objects.filter(
                project=self.project,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)