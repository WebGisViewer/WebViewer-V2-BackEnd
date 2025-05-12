# layers/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import ProjectLayerData, ProjectLayer


@receiver(post_save, sender=ProjectLayerData)
def update_layer_on_feature_save(sender, instance, created, **kwargs):
    """Update layer metadata when features are saved."""
    # Skip if we're just updating a handful of attributes
    update_fields = kwargs.get('update_fields')
    if update_fields and 'geometry' not in update_fields and 'properties' not in update_fields:
        return

    # Update the layer's last data update time
    layer = instance.project_layer
    layer.last_data_update = timezone.now()
    layer.save(update_fields=['last_data_update'])


@receiver(post_delete, sender=ProjectLayerData)
def update_layer_on_feature_delete(sender, instance, **kwargs):
    """Update layer metadata when features are deleted."""
    layer = instance.project_layer
    layer.last_data_update = timezone.now()
    layer.feature_count = layer.features.count()  # Recalculate
    layer.save(update_fields=['last_data_update', 'feature_count'])