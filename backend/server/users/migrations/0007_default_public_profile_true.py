from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_customuser_default_currency'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='public_profile',
            field=models.BooleanField(default=True),
        ),
    ]
