# styling/apps.py
from django.apps import AppConfig

class StylingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'styling'
    verbose_name = 'Map Styling'