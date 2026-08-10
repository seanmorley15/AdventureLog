from django.db import migrations, models
from users.models import BASEMAP_CHOICES


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0076_normalize_all_day_visit_end_dates'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='map_style',
            field=models.CharField(choices=BASEMAP_CHOICES, default='default', max_length=32),
        ),
    ]
