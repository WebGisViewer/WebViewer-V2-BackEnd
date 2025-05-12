# projects/models.py
from django.db import models
from django.utils import timezone


class Project(models.Model):
    """Project model representing a map project with configuration."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Spatial configuration
    default_center_lat = models.FloatField(default=0)
    default_center_lng = models.FloatField(default=0)
    default_zoom_level = models.IntegerField(default=5)

    # Configuration options stored as JSON
    map_controls = models.JSONField(default=dict, blank=True)
    map_options = models.JSONField(default=dict, blank=True)

    # Zoom constraints
    max_zoom = models.IntegerField(default=18)
    min_zoom = models.IntegerField(default=1)

    # Timestamps and creator
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_projects'
    )

    class Meta:
        db_table = 'projects_wiroi_online'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)