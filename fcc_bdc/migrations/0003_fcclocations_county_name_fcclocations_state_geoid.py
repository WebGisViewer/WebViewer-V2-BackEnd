# Generated by Django 4.2.2 on 2025-06-23 06:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fcc_bdc", "0002_fcclocations_geom"),
    ]

    operations = [
        migrations.AddField(
            model_name="fcclocations",
            name="county_name",
            field=models.CharField(null=True),
        ),
        migrations.AddField(
            model_name="fcclocations",
            name="state_geoid",
            field=models.BigIntegerField(null=True),
        ),
    ]
