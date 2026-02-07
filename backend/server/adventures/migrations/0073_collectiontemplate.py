# Generated manually for CollectionTemplate model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('adventures', '0072_transportation_collection_lodging_collection'),
    ]

    operations = [
        migrations.CreateModel(
            name='CollectionTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('template_data', models.JSONField(default=dict)),
                ('is_public', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collection_templates', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
