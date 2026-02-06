# Migration to add soft-delete fields to ContentImage and ContentAttachment

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('adventures', '0073_populate_visit_users'),
    ]

    operations = [
        # ContentImage soft-delete fields
        migrations.AddField(
            model_name='contentimage',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='contentimage',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='contentimage',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='deleted_images',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # ContentAttachment soft-delete fields
        migrations.AddField(
            model_name='contentattachment',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='contentattachment',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='contentattachment',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='deleted_attachments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
