from django.db import migrations, models

from core.timezones import TIMEZONES

CHOICES = [(tz, tz) for tz in TIMEZONES]


def tz_field(**kwargs):
    return models.CharField(blank=True, choices=CHOICES, max_length=50, null=True, **kwargs)


class Migration(migrations.Migration):
    """Browsers set to UTC report "UTC", which was missing from the timezone choices."""

    dependencies = [
        ('adventures', '0086_file_path_indexes'),
    ]

    operations = [
        migrations.AlterField(model_name='visit', name='timezone', field=tz_field()),
        migrations.AlterField(model_name='lodging', name='timezone', field=tz_field()),
        migrations.AlterField(model_name='activity', name='timezone', field=tz_field()),
        migrations.AlterField(model_name='transportation', name='start_timezone', field=tz_field()),
        migrations.AlterField(model_name='transportation', name='end_timezone', field=tz_field()),
    ]
