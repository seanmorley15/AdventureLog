from django.db import migrations


def convert_remaining_trips(apps, schema_editor):
    """Turn every dated trip that is still date-keyed into a day plan.

    Migration 0079 converted trips of 21 days or fewer. This pass uses the
    same idempotent conversion with no length cap, so a trip that already
    has day indexes is left as it is. Folders and trips without a positive
    date span are left unchanged.
    """
    from adventures.services.day_plan import convert_collection

    Collection = apps.get_model('adventures', 'Collection')
    for collection in Collection.objects.filter(type='trip').iterator():
        convert_collection(collection, apps=apps)


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0079_convert_trips_to_day_plans'),
    ]

    operations = [
        migrations.RunPython(convert_remaining_trips, migrations.RunPython.noop),
    ]
