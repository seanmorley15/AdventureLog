# Generated by Django 5.0.8 on 2024-08-15 23:31

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0001_adventure_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adventureimage',
            name='adventure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='adventures.adventure'),
        ),
    ]
