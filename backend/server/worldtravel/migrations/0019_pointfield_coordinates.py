# Generated manually for PostGIS PointField migration

from django.contrib.gis.geos import Point
from django.db import migrations
import django.contrib.gis.db.models.fields


def forwards_fill_coordinates(apps, schema_editor):
    for model_name in ('Country', 'Region', 'City'):
        Model = apps.get_model('worldtravel', model_name)
        for row in Model.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).iterator():
            row.coordinates = Point(float(row.longitude), float(row.latitude), srid=4326)
            row.save(update_fields=['coordinates'])


class Migration(migrations.Migration):

    dependencies = [
        ('worldtravel', '0018_rename_user_id_visitedcity_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='coordinates',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='region',
            name='coordinates',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='city',
            name='coordinates',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.RunPython(forwards_fill_coordinates, migrations.RunPython.noop),
        migrations.RemoveField(model_name='country', name='latitude'),
        migrations.RemoveField(model_name='country', name='longitude'),
        migrations.RemoveField(model_name='region', name='latitude'),
        migrations.RemoveField(model_name='region', name='longitude'),
        migrations.RemoveField(model_name='city', name='latitude'),
        migrations.RemoveField(model_name='city', name='longitude'),
    ]
