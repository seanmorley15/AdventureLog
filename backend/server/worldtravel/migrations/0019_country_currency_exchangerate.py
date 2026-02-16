# Generated manually for currency support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worldtravel', '0018_rename_user_id_visitedcity_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='currency_code',
            field=models.CharField(blank=True, help_text='ISO 4217 currency code (e.g., USD, EUR)', max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='country',
            name='currency_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='country',
            name='currency_symbol',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.CreateModel(
            name='ExchangeRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency_code', models.CharField(help_text='ISO 4217 currency code', max_length=3, unique=True)),
                ('rate', models.DecimalField(decimal_places=8, help_text='Rate relative to 1 USD', max_digits=18)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Exchange Rate',
                'verbose_name_plural': 'Exchange Rates',
                'ordering': ['currency_code'],
            },
        ),
    ]
