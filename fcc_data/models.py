
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

from django.db import models
from django.contrib.gis.db import models as gis_models

class FCCLocations(models.Model):
    fcc_location_id = models.BigIntegerField()
    lat = models.FloatField()
    long = models.FloatField()
    state_name = models.CharField(max_length=100)
    county_name = models.CharField(max_length=100)
    state_geoid = models.BigIntegerField()
    county_geoid = models.BigIntegerField()


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fcc_bdc_rel6'
        ordering = ['state_name']

    def __str__(self):
        return f"{self.fcc_location_id} ({self.state_name})"

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)