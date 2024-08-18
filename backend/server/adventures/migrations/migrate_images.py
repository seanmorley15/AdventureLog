from django.db import migrations

def move_images_to_new_model(apps, schema_editor):
    Adventure = apps.get_model('adventures', 'Adventure')
    AdventureImage = apps.get_model('adventures', 'AdventureImage')

    for adventure in Adventure.objects.all():
        if adventure.image:
            AdventureImage.objects.create(
                adventure=adventure,
                image=adventure.image,
                user_id=adventure.user_id,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0001_initial'),
        ('adventures', '0002_adventureimage'),
    ]

    operations = [
        migrations.RunPython(move_images_to_new_model),
        migrations.RemoveField(
            model_name='Adventure',
            name='image',
        ),
    ]