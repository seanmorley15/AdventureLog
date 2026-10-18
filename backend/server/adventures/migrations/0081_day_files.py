import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0080_convert_remaining_trips_to_day_plans'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='collection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='idea_activities', to='adventures.collection'),
        ),
        migrations.AddField(
            model_name='activity',
            name='day',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='adventures.collectionitineraryday'),
        ),
        migrations.AddField(
            model_name='activity',
            name='promoted_activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='promoted_from', to='adventures.activity'),
        ),
        migrations.AlterField(
            model_name='activity',
            name='visit',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='adventures.visit'),
        ),
        migrations.AddField(
            model_name='trail',
            name='collection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='idea_trails', to='adventures.collection'),
        ),
        migrations.AddField(
            model_name='trail',
            name='day',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trails', to='adventures.collectionitineraryday'),
        ),
        migrations.AddField(
            model_name='trail',
            name='span_end_index',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='trail',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trails', to='adventures.location'),
        ),
        migrations.AddConstraint(
            model_name='activity',
            constraint=models.CheckConstraint(
                check=(
                    Q(visit__isnull=False, day__isnull=True, collection__isnull=True)
                    | Q(visit__isnull=True, day__isnull=False, collection__isnull=True)
                    | Q(visit__isnull=True, day__isnull=True, collection__isnull=False)
                ),
                name='activity_exactly_one_parent',
            ),
        ),
        migrations.AddConstraint(
            model_name='trail',
            constraint=models.CheckConstraint(
                check=(
                    Q(location__isnull=False, day__isnull=True, collection__isnull=True)
                    | Q(location__isnull=True, day__isnull=False, collection__isnull=True)
                    | Q(location__isnull=True, day__isnull=True, collection__isnull=False)
                ),
                name='trail_exactly_one_parent',
            ),
        ),
    ]
