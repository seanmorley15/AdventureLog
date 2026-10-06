from django.db import migrations


def convert_trips(apps, schema_editor):
    from adventures.utils.itinerary_days import convert_collection

    Collection = apps.get_model('adventures', 'Collection')
    for collection in Collection.objects.filter(type='trip').iterator():
        convert_collection(collection, apps=apps)


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0078_itinerary_days_placements'),
    ]

    operations = [
        migrations.RunPython(convert_trips, migrations.RunPython.noop),
    ]
