# Generated manually - PR #999 Entity System Overhaul
# Consolidates deploy migrations 0072, 0074-0077, 0079-0081, 0085

import uuid
import django.contrib.postgres.fields
import django.db.models.deletion
import djmoney.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0075_auditlog'),
    ]

    operations = [
        # ===== Visit model expansion =====
        # Make location nullable (visits can now be for transportation or lodging)
        migrations.AlterField(
            model_name='visit',
            name='location',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='visits',
                to='adventures.location',
            ),
        ),
        # Add transportation FK
        migrations.AddField(
            model_name='visit',
            name='transportation',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='visits',
                to='adventures.transportation',
            ),
        ),
        # Add lodging FK
        migrations.AddField(
            model_name='visit',
            name='lodging',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='visits',
                to='adventures.lodging',
            ),
        ),
        # Add rating
        migrations.AddField(
            model_name='visit',
            name='rating',
            field=models.FloatField(blank=True, null=True),
        ),
        # Add price tracking
        migrations.AddField(
            model_name='visit',
            name='total_price_currency',
            field=djmoney.models.fields.CurrencyField(
                default='USD', editable=False, max_length=3,
            ),
        ),
        migrations.AddField(
            model_name='visit',
            name='total_price',
            field=djmoney.models.fields.MoneyField(
                blank=True, decimal_places=2,
                default_currency='USD', max_digits=12, null=True,
            ),
        ),
        migrations.AddField(
            model_name='visit',
            name='number_of_people',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        # Add visit-collection link
        migrations.AddField(
            model_name='visit',
            name='collection',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='planned_visits',
                to='adventures.collection',
            ),
        ),

        # ===== Transportation & Lodging tags =====
        migrations.AddField(
            model_name='transportation',
            name='tags',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=100),
                blank=True, null=True, size=None,
            ),
        ),
        migrations.AddField(
            model_name='lodging',
            name='tags',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=100),
                blank=True, null=True, size=None,
            ),
        ),

        # ===== Transportation & Lodging M2M collections (fresh, no FK migration needed) =====
        migrations.AddField(
            model_name='transportation',
            name='collections',
            field=models.ManyToManyField(
                blank=True, related_name='transportations',
                to='adventures.collection',
            ),
        ),
        migrations.AddField(
            model_name='lodging',
            name='collections',
            field=models.ManyToManyField(
                blank=True, related_name='lodgings',
                to='adventures.collection',
            ),
        ),

        # ===== Cached average ratings =====
        migrations.AddField(
            model_name='location',
            name='average_rating',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transportation',
            name='average_rating',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='lodging',
            name='average_rating',
            field=models.FloatField(blank=True, null=True),
        ),

        # ===== Country fields on Transportation & Lodging =====
        migrations.AddField(
            model_name='transportation',
            name='origin_country',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='transportation_origins',
                to='worldtravel.country',
            ),
        ),
        migrations.AddField(
            model_name='transportation',
            name='destination_country',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='transportation_destinations',
                to='worldtravel.country',
            ),
        ),
        migrations.AddField(
            model_name='lodging',
            name='country',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lodgings',
                to='worldtravel.country',
            ),
        ),
        migrations.AddField(
            model_name='lodging',
            name='region',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lodgings',
                to='worldtravel.region',
            ),
        ),
        migrations.AddField(
            model_name='lodging',
            name='city',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lodgings',
                to='worldtravel.city',
            ),
        ),
    ]
