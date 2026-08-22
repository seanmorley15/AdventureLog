from datetime import timezone as dt_timezone

from django.db import migrations
from django.utils import timezone


def make_visit_dates_aware(apps, schema_editor):
    Visit = apps.get_model('adventures', 'Visit')
    db_alias = schema_editor.connection.alias

    for visit in Visit.objects.using(db_alias).iterator():
        updated_fields = []

        if visit.start_date and timezone.is_naive(visit.start_date):
            visit.start_date = timezone.make_aware(visit.start_date, dt_timezone.utc)
            updated_fields.append('start_date')

        if visit.end_date and timezone.is_naive(visit.end_date):
            visit.end_date = timezone.make_aware(visit.end_date, dt_timezone.utc)
            updated_fields.append('end_date')

        if updated_fields:
            visit.save(update_fields=updated_fields)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0074_contentimage_source_metadata'),
    ]

    operations = [
        migrations.RunPython(make_visit_dates_aware, noop),
    ]
