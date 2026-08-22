# Generated manually for PostGIS PointField migration

from django.contrib.gis.geos import Point
from django.db import migrations
import django.contrib.gis.db.models.fields


def forwards_fill_points(apps, schema_editor):
    Location = apps.get_model('adventures', 'Location')
    for row in Location.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).iterator():
        row.coordinates = Point(float(row.longitude), float(row.latitude), srid=4326)
        row.save(update_fields=['coordinates'])

    Lodging = apps.get_model('adventures', 'Lodging')
    for row in Lodging.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).iterator():
        row.coordinates = Point(float(row.longitude), float(row.latitude), srid=4326)
        row.save(update_fields=['coordinates'])

    Transportation = apps.get_model('adventures', 'Transportation')
    for row in Transportation.objects.iterator():
        update_fields = []
        if row.origin_latitude is not None and row.origin_longitude is not None:
            row.origin = Point(float(row.origin_longitude), float(row.origin_latitude), srid=4326)
            update_fields.append('origin')
        if row.destination_latitude is not None and row.destination_longitude is not None:
            row.destination = Point(
                float(row.destination_longitude), float(row.destination_latitude), srid=4326
            )
            update_fields.append('destination')
        if update_fields:
            row.save(update_fields=update_fields)

    Activity = apps.get_model('adventures', 'Activity')
    for row in Activity.objects.iterator():
        update_fields = []
        if row.start_lat is not None and row.start_lng is not None:
            row.start_point = Point(float(row.start_lng), float(row.start_lat), srid=4326)
            update_fields.append('start_point')
        if row.end_lat is not None and row.end_lng is not None:
            row.end_point = Point(float(row.end_lng), float(row.end_lat), srid=4326)
            update_fields.append('end_point')
        if update_fields:
            row.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0072_trail_wanderer_author_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='coordinates',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='lodging',
            name='coordinates',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='transportation',
            name='origin',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='transportation',
            name='destination',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='activity',
            name='start_point',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='activity',
            name='end_point',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.RunPython(forwards_fill_points, migrations.RunPython.noop),
        migrations.RemoveField(model_name='location', name='latitude'),
        migrations.RemoveField(model_name='location', name='longitude'),
        migrations.RemoveField(model_name='lodging', name='latitude'),
        migrations.RemoveField(model_name='lodging', name='longitude'),
        migrations.RemoveField(model_name='transportation', name='origin_latitude'),
        migrations.RemoveField(model_name='transportation', name='origin_longitude'),
        migrations.RemoveField(model_name='transportation', name='destination_latitude'),
        migrations.RemoveField(model_name='transportation', name='destination_longitude'),
        migrations.RemoveField(model_name='activity', name='start_lat'),
        migrations.RemoveField(model_name='activity', name='start_lng'),
        migrations.RemoveField(model_name='activity', name='end_lat'),
        migrations.RemoveField(model_name='activity', name='end_lng'),
    ]
