from datetime import datetime, time, timezone as dt_timezone

from django.db import migrations
from django.utils import timezone


def _ensure_aware(value):
    if value is None:
        return None
    if timezone.is_naive(value):
        return timezone.make_aware(value, dt_timezone.utc)
    return value


def _is_midnight_utc(value):
    if value is None:
        return False
    utc_value = _ensure_aware(value).astimezone(dt_timezone.utc)
    return utc_value.time() == time.min


def _is_end_of_day_utc(value):
    if value is None:
        return False
    utc_value = _ensure_aware(value).astimezone(dt_timezone.utc)
    return utc_value.time() == time.max


def normalize_all_day_visit_end_dates(apps, schema_editor):
    Visit = apps.get_model('adventures', 'Visit')
    db_alias = schema_editor.connection.alias

    for visit in Visit.objects.using(db_alias).iterator():
        if not visit.start_date or not visit.end_date:
            continue

        if not _is_midnight_utc(visit.start_date):
            continue

        if not (_is_midnight_utc(visit.end_date) or _is_end_of_day_utc(visit.end_date)):
            continue

        normalized_end = timezone.make_aware(
            datetime.combine(visit.end_date.date(), time.min),
            dt_timezone.utc,
        )

        if visit.end_date != normalized_end:
            visit.end_date = normalized_end
            visit.save(update_fields=['end_date'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0075_make_visit_dates_timezone_aware'),
    ]

    operations = [
        migrations.RunPython(normalize_all_day_visit_end_dates, noop),
    ]
