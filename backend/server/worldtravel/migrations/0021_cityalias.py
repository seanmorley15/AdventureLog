from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('worldtravel', '0020_native_names_and_territories'),
    ]

    operations = [
        migrations.CreateModel(
            name='CityAlias',
            fields=[
                ('old_id', models.CharField(primary_key=True, serialize=False)),
                (
                    'city',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name='aliases', to='worldtravel.city'
                    ),
                ),
            ],
            options={
                'verbose_name_plural': 'City aliases',
            },
        ),
    ]
