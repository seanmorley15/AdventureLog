from django.db import migrations

def set_end_date_equal_to_start(apps, schema_editor):
    Visit = apps.get_model('adventures', 'Visit')
    for visit in Visit.objects.filter(end_date__isnull=True):
        if visit.start_date:
            visit.end_date = visit.start_date
            visit.save()

class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0029_adventure_city_adventure_country_adventure_region'),
    ]

    operations = [
        migrations.RunPython(set_end_date_equal_to_start),
    ]
