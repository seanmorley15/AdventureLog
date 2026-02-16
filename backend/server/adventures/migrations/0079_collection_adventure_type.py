from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0078_adventure_types_and_sports'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='adventure_type',
            field=models.ForeignKey(
                blank=True,
                help_text='Category/type of this collection',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='collections',
                to='adventures.adventuretype'
            ),
        ),
    ]
