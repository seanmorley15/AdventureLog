from django.db import migrations, models


def empty_emails_to_null(apps, schema_editor):
    CustomUser = apps.get_model('users', 'CustomUser')
    CustomUser.objects.filter(email='').update(email=None)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_customuser_date_format'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
        migrations.RunPython(empty_emails_to_null, migrations.RunPython.noop),
    ]
