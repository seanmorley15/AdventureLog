from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction. It builds the index
    # without blocking writes, which matters on installs with many photos.
    atomic = False

    dependencies = [
        ('adventures', '0084_itinerary_item_target_index'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='contentimage',
            index=models.Index(fields=['immich_id'], name='contentimage_immich_idx'),
        ),
    ]
