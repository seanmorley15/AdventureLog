from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0079_collection_adventure_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='is_public',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='collection',
            name='is_public',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='transportation',
            name='is_public',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='lodging',
            name='is_public',
            field=models.BooleanField(default=True),
        ),
    ]
