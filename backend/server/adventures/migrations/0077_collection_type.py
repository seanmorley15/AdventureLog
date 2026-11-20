from django.db import migrations, models

from adventures.utils.collection_type import assign_collection_type_from_dates


def set_collection_types(apps, schema_editor):
    """Both dates mean trip. Otherwise folder. Leave dates and itinerary rows."""
    Collection = apps.get_model('adventures', 'Collection')
    db_alias = schema_editor.connection.alias
    for collection in Collection.objects.using(db_alias).iterator():
        new_type = assign_collection_type_from_dates(collection.start_date, collection.end_date)
        if collection.type != new_type:
            Collection.objects.using(db_alias).filter(pk=collection.pk).update(type=new_type)


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0076_normalize_all_day_visit_end_dates'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='type',
            field=models.CharField(
                choices=[('folder', 'Folder'), ('trip', 'Trip')],
                default='folder',
                max_length=10,
            ),
        ),
        migrations.RunPython(set_collection_types, migrations.RunPython.noop),
    ]
