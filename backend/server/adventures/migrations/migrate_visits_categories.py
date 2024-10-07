from django.db import migrations
from django.db import migrations, models

def move_images_to_new_model(apps, schema_editor):
    Adventure = apps.get_model('adventures', 'Adventure')
    Visit = apps.get_model('adventures', 'Visit')

    for adventure in Adventure.objects.all():
        # if the type is visited and there is no date, set note to 'No date provided.'
        note = 'No date provided.' if adventure.type == 'visited' and not adventure.date else ''
        if adventure.date or adventure.type == 'visited':
            Visit.objects.create(
                adventure=adventure,
                start_date=adventure.date,
                end_date=adventure.end_date,
                notes=note,
            )
        if adventure.type == 'visited' or adventure.type == 'planned':
            adventure.type = 'general'
            adventure.save()


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0007_visit_model'),
    ]

    operations = [
        migrations.RunPython(move_images_to_new_model),
    ]