from django.contrib.gis.geos import Point
from django.db import migrations, models
import django.contrib.gis.db.models.fields


def backfill_image_source(apps, schema_editor):
    ContentImage = apps.get_model('adventures', 'ContentImage')
    ContentImage.objects.filter(immich_id__isnull=False).exclude(immich_id='').update(
        source='immich'
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0073_pointfield_geography'),
    ]

    operations = [
        migrations.AddField(
            model_name='contentimage',
            name='source',
            field=models.CharField(
                choices=[
                    ('upload', 'Upload'),
                    ('google', 'Google'),
                    ('wikipedia', 'Wikipedia'),
                    ('url', 'URL'),
                    ('immich', 'Immich'),
                ],
                default='upload',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='contentimage',
            name='source_url',
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name='contentimage',
            name='coordinates',
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True, null=True, srid=4326
            ),
        ),
        migrations.RunPython(backfill_image_source, noop),
    ]
