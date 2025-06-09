# layers/models.py
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
from django.contrib.gis.gdal import SpatialReference


class LayerType(models.Model):
    """
    Defines types of map layers available in the system.

    Examples: Point Layer, Polygon Layer, Line Layer, Heatmap, etc.
    """
    type_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    default_style = models.JSONField(default=dict)
    icon_type = models.CharField(max_length=50, blank=True, null=True)
    icon_options = models.JSONField(default=dict, blank=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'layer_types_wiroi_online'
        ordering = ['type_name']

    def __str__(self):
        return self.type_name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)



class ProjectLayerGroup(models.Model):
    """
    Groups of layers within a project for organization.

    Examples: Base Layers, Analysis Layers, Customer Data, etc.
    """
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='layer_groups')
    name = models.CharField(max_length=100)
    display_order = models.IntegerField(default=0)
    is_visible_by_default = models.BooleanField(default=True)
    is_expanded_by_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_layer_groups_wiroi_online'
        ordering = ['project', 'display_order']
        unique_together = ('project', 'name')

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

class ProjectLayer(models.Model):
    """
    Individual map layers within a project group.

    This is the core model that connects styling, data, and behaviors.
    """
    project_layer_group = models.ForeignKey(
        ProjectLayerGroup,
        on_delete=models.CASCADE,
        related_name='layers'
    )
    layer_type = models.ForeignKey(
        LayerType,
        on_delete=models.PROTECT,
        related_name='layers'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    # Visual styling
    style = models.JSONField(default=dict, blank=True)
    z_index = models.IntegerField(default=0)

    # Visibility settings
    is_visible_by_default = models.BooleanField(default=True)
    min_zoom_visibility = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(22)]
    )
    max_zoom_visibility = models.IntegerField(
        default=22,
        validators=[MinValueValidator(0), MaxValueValidator(22)]
    )

    # For point layers
    marker_type = models.CharField(max_length=50, blank=True, null=True)
    marker_image_url = models.CharField(max_length=255, blank=True, null=True)
    marker_options = models.JSONField(default=dict, blank=True)

    # Feature display options
    enable_clustering = models.BooleanField(default=False)
    clustering_options = models.JSONField(default=dict, blank=True)
    enable_labels = models.BooleanField(default=False)
    label_options = models.JSONField(default=dict, blank=True)

    # Foreign keys that will be implemented in other apps
    # These will be commented out until those apps exist
    # marker_library = models.ForeignKey('styling.MarkerLibrary', on_delete=models.SET_NULL, null=True, blank=True, related_name='layers')
    # popup_template = models.ForeignKey('styling.PopupTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='layers')
    marker_library = models.ForeignKey('styling.MarkerLibrary', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='layers')
    popup_template = models.ForeignKey('styling.PopupTemplate', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='layers')
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data_source = models.CharField(max_length=255, blank=True, null=True)
    attribution = models.CharField(max_length=255, blank=True, null=True)

    # Data statistics (updated when features are added/removed)
    feature_count = models.IntegerField(default=0)
    last_data_update = models.DateTimeField(null=True, blank=True)

    is_public = models.BooleanField(
        default=False,
        help_text="Whether this layer is visible to unauthenticated users via shared links"
    )

    original_crs = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Original CRS of the uploaded data"
    )
    target_crs = models.CharField(
        max_length=100,
        default="EPSG:4326",
        help_text="Target CRS for storing geometries"
    )
    upload_file_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Original file type of uploaded data"
    )
    upload_file_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Original file name of uploaded data"
    )
    upload_status = models.CharField(
        max_length=50,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("crs_needed", "CRS Needed"),
            ("importing", "Importing"),
            ("complete", "Complete"),
            ("failed", "Failed")
        ],
        help_text="Current status of file upload/import process"
    )
    upload_error = models.TextField(
        blank=True,
        null=True,
        help_text="Error details if upload failed"
    )
    class Meta:
        db_table = 'project_layers_wiroi_online'
        ordering = ['project_layer_group', 'z_index']
        unique_together = ('project_layer_group', 'name')

    def __str__(self):
        return f"{self.project_layer_group.project.name} - {self.name}"

    @property
    def project(self):
        """Get the project this layer belongs to."""
        return self.project_layer_group.project

    def update_feature_count(self):
        """Update the feature count for this layer."""
        self.feature_count = self.features.count()
        self.last_data_update = timezone.now()
        self.save(update_fields=['feature_count', 'last_data_update'])

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

class ProjectLayerData(models.Model):
    """
    Actual geospatial feature data for a layer.

    Stores individual geographic features with properties.
    """
    project_layer = models.ForeignKey(
        ProjectLayer,
        on_delete=models.CASCADE,
        related_name='features'
    )
    # GeoDjango geometric field - can store any geometry type (point, line, polygon)
    geometry = models.GeometryField(srid=4326)
    # Properties to be displayed in popups or used for styling
    properties = models.JSONField(default=dict)
    # Unique identifier for external reference
    feature_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional bounding box for quick spatial queries
    bbox = models.PolygonField(null=True, blank=True, srid=4326)

    class Meta:
        db_table = 'project_layer_data_wiroi_online'
        indexes = [
            models.Index(fields=['project_layer', 'feature_id']),
            models.Index(fields=['project_layer', 'created_at']),
        ]

    def __str__(self):
        return f"Feature {self.feature_id or self.id} - {self.project_layer.name}"

    def save(self, *args, **kwargs):
        # Generate feature_id if not provided
        if not self.feature_id:
            self.feature_id = str(uuid.uuid4())

        # Calculate bounding box for geometry
        if self.geometry and not self.bbox:
            if self.geometry.geom_type == 'Point':
                # For points, create a small box around the point
                # to make a valid polygon bbox
                from django.contrib.gis.geos import Polygon
                x, y = self.geometry.coords
                buffer = 0.0001  # Small buffer (~10m at equator)
                self.bbox = Polygon(
                    ((x - buffer, y - buffer),
                     (x - buffer, y + buffer),
                     (x + buffer, y + buffer),
                     (x + buffer, y - buffer),
                     (x - buffer, y - buffer))
                )
            else:
                # For other geometry types, use the envelope
                self.bbox = self.geometry.envelope

        # Save the feature
        super().save(*args, **kwargs)

        # Update feature count on the layer
        self.project_layer.update_feature_count()

class LayerPermission(models.Model):
    """
    Fine-grained permissions for layer access.

    Controls which clients can view, edit, or export specific layers.
    """
    project_layer = models.ForeignKey(
        ProjectLayer,
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    client_project = models.ForeignKey(
        'clients.ClientProject',
        on_delete=models.CASCADE,
        related_name='layer_permissions'
    )
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'layer_permissions_wiroi_online'
        unique_together = ('project_layer', 'client_project')

    def __str__(self):
        return f"{self.project_layer.name} - {self.client_project.client.name}"