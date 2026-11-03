from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('worldtravel', '0019_pointfield_coordinates'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='native_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='region',
            name='native_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='region',
            name='territory',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='territory_regions',
                to='worldtravel.country',
            ),
        ),
    ]
