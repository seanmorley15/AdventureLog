# Generated manually for collaborative mode user tracking

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('adventures', '0071_alter_collectionitineraryitem_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='visits', to=settings.AUTH_USER_MODEL),
        ),
    ]
