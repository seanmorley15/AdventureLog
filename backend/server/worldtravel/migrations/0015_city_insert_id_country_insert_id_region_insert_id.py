# Generated by Django 5.0.8 on 2025-01-13 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worldtravel', '0014_alter_visitedcity_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='insert_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='country',
            name='insert_id',
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='region',
            name='insert_id',
            field=models.UUIDField(blank=True, null=True),
        ),
    ]
