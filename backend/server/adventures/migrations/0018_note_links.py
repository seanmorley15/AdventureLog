# Generated by Django 5.0.7 on 2024-08-04 13:19

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0017_alter_note_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='links',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.URLField(), blank=True, null=True, size=None),
        ),
    ]
