from django.db import migrations, models


def copy_public_profile(apps, schema_editor):
    """Public profiles stay public; every other profile stays private."""
    User = apps.get_model('users', 'CustomUser')
    User.objects.filter(public_profile=True).update(profile_visibility='public')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_customuser_legacy_email_login'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='profile_visibility',
            field=models.CharField(
                choices=[('private', 'Private'), ('signed_in', 'Signed-in users'), ('public', 'Public')],
                default='private',
                max_length=10,
            ),
        ),
        migrations.RunPython(copy_public_profile, migrations.RunPython.noop),
    ]
