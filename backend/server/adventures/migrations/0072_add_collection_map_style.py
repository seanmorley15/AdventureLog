from django.db import migrations, models
from users.models import BASEMAP_CHOICES


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0071_alter_collectionitineraryitem_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='map_style',
            field=models.CharField(choices=BASEMAP_CHOICES, default='default', max_length=32),
        ),
    ]
