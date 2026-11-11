from django.db import migrations, models
from django.db.models.functions import Lower


def grandfather_existing_emails(apps, schema_editor):
    """Let every account that exists today keep signing in by email through social login."""
    User = apps.get_model('users', 'CustomUser')
    User.objects.exclude(email__isnull=True).exclude(email='').update(legacy_email_login=Lower('email'))


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_mobileauthcode'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='legacy_email_login',
            field=models.EmailField(blank=True, editable=False, max_length=254, null=True),
        ),
        migrations.RunPython(grandfather_existing_emails, migrations.RunPython.noop),
    ]
