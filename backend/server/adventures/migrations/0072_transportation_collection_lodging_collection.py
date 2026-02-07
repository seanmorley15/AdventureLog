# Generated manually for collection field on Transportation and Lodging

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0071_alter_collectionitineraryitem_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transportation',
            name='collection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='adventures.collection'),
        ),
        migrations.AddField(
            model_name='lodging',
            name='collection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='adventures.collection'),
        ),
        migrations.AddField(
            model_name='note',
            name='collection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='adventures.collection'),
        ),
        migrations.AddField(
            model_name='checklist',
            name='collection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='adventures.collection'),
        ),
    ]
