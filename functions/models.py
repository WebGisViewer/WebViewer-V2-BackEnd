# functions/models.py
from django.db import models
from django.utils import timezone


class LayerFunction(models.Model):
    """
    Reusable behaviors that can be applied to map layers.

    Examples include clustering, filtering, data analysis,
    symbology rules, and other dynamic behaviors.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Function type and configuration
    function_type = models.CharField(
        max_length=50,
        choices=[
            ('clustering', 'Point Clustering'),
            ('filtering', 'Feature Filtering'),
            ('styling', 'Dynamic Styling'),
            ('analysis', 'Data Analysis'),
            ('labeling', 'Feature Labeling'),
            ('heatmap', 'Heat Map'),
            ('animation', 'Animation'),
            ('interaction', 'Custom Interaction'),
            ('format', 'Data Formatting'),
            ('transform', 'Geometry Transform')
        ],
        default='clustering'
    )

    # Function implementation
    function_code = models.TextField(
        blank=True,
        null=True,
        help_text="JavaScript code implementing the function"
    )

    # Default configuration
    function_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default configuration for the function"
    )

    # Metadata
    is_system = models.BooleanField(default=False)
    created_by_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'layer_functions_wiroi_online'
        verbose_name = 'Layer Function'
        verbose_name_plural = 'Layer Functions'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ProjectLayerFunction(models.Model):
    """
    Association between layers and functions with configuration.

    This junction table specifies which functions are applied
    to which layers, along with custom configurations.
    """
    project_layer = models.ForeignKey('layers.ProjectLayer', on_delete=models.CASCADE, related_name='functions')
    layer_function = models.ForeignKey(LayerFunction, on_delete=models.CASCADE, related_name='layer_instances')

    # Function arguments for this instance
    function_arguments = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arguments specific to this function instance"
    )

    # Configuration for this specific application of the function
    enabled = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=0,
        help_text="Priority for function execution order (higher = earlier)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_layer_functions_wiroi_online'
        verbose_name = 'Project Layer Function'
        verbose_name_plural = 'Project Layer Functions'
        ordering = ['-priority', 'created_at']
        unique_together = ('project_layer', 'layer_function')

    def __str__(self):
        return f"{self.project_layer.name} - {self.layer_function.name}"

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class MapTool(models.Model):
    """
    Interactive tools available for maps.

    Examples include measurement tools, drawing tools,
    data exporters, and other user interactions.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Tool type
    tool_type = models.CharField(
        max_length=50,
        choices=[
            ('measure_distance', 'Measure Distance'),
            ('measure_area', 'Measure Area'),
            ('draw_point', 'Draw Point'),
            ('draw_line', 'Draw Line'),
            ('draw_polygon', 'Draw Polygon'),
            ('export_data', 'Export Data'),
            ('print', 'Print Map'),
            ('search', 'Search Features'),
            ('select', 'Select Features'),
            ('edit', 'Edit Features'),
            ('custom', 'Custom Tool')
        ],
        default='measure_distance'
    )

    # Tool icon
    icon = models.CharField(max_length=100, blank=True, null=True)

    # Tool implementation
    tool_code = models.TextField(
        blank=True,
        null=True,
        help_text="JavaScript code implementing the tool"
    )

    # Default options
    default_options = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default options for the tool"
    )

    # UI position
    ui_position = models.CharField(
        max_length=50,
        choices=[
            ('topright', 'Top Right'),
            ('topleft', 'Top Left'),
            ('bottomright', 'Bottom Right'),
            ('bottomleft', 'Bottom Left'),
            ('standalone', 'Standalone/Floating')
        ],
        default='topright'
    )

    # Metadata
    is_system = models.BooleanField(default=False)
    created_by_user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'map_tools_wiroi_online'
        verbose_name = 'Map Tool'
        verbose_name_plural = 'Map Tools'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ProjectTool(models.Model):
    """
    Tools configured for a specific project.

    This junction table specifies which tools are available
    in which projects, along with display order and custom options.
    """
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='tools')
    tool = models.ForeignKey(MapTool, on_delete=models.CASCADE, related_name='project_instances')

    # Tool configuration
    is_enabled = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    # Custom options for this project
    tool_options = models.JSONField(
        default=dict,
        blank=True,
        help_text="Project-specific tool options"
    )

    # Custom positioning
    custom_position = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Override the default UI position"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_tools_wiroi_online'
        verbose_name = 'Project Tool'
        verbose_name_plural = 'Project Tools'
        ordering = ['project', 'display_order']
        unique_together = ('project', 'tool')

    def __str__(self):
        return f"{self.project.name} - {self.tool.name}"

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)