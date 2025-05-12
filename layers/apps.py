# layers/apps.py
from django.apps import AppConfig

class LayersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'layers'
    verbose_name = 'Map Layers'

    def ready(self):
        import layers.signals  # Register signals