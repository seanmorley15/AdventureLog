# Generated by Django 5.0.7 on 2024-08-04 02:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0016_alter_note_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='note',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
