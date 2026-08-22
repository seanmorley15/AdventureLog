from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0071_alter_collectionitineraryitem_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='trail',
            name='wanderer_author_username',
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name='Wanderer Author Username',
            ),
        ),
        migrations.AddField(
            model_name='trail',
            name='wanderer_author_domain',
            field=models.CharField(
                blank=True,
                help_text="Author's Wanderer instance domain for /trail/view/@user@domain/id links.",
                max_length=255,
                null=True,
                verbose_name='Wanderer Author Domain',
            ),
        ),
    ]
