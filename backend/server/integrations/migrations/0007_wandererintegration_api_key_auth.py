from django.db import migrations, models


def delete_existing_wanderer_integrations(apps, schema_editor):
    WandererIntegration = apps.get_model('integrations', 'WandererIntegration')
    WandererIntegration.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0006_alter_wandererintegration_token'),
    ]

    operations = [
        migrations.RunPython(
            delete_existing_wanderer_integrations,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name='wandererintegration',
            name='username',
        ),
        migrations.RemoveField(
            model_name='wandererintegration',
            name='token',
        ),
        migrations.RemoveField(
            model_name='wandererintegration',
            name='token_expiry',
        ),
        migrations.AddField(
            model_name='wandererintegration',
            name='api_key',
            field=models.CharField(default='', max_length=512),
            preserve_default=False,
        ),
    ]
