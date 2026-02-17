# Data migration to populate user field on existing visits

from django.db import migrations


def populate_visit_users(apps, schema_editor):
    """
    Assign existing visits to the location's owner.
    This ensures existing visits have a user for display purposes.
    """
    Visit = apps.get_model('adventures', 'Visit')

    for visit in Visit.objects.filter(user__isnull=True).select_related('location'):
        if visit.location and visit.location.user:
            visit.user = visit.location.user
            visit.save(update_fields=['user'])


def reverse_populate(apps, schema_editor):
    """Reverse migration - clear user from visits."""
    Visit = apps.get_model('adventures', 'Visit')
    Visit.objects.update(user=None)


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0072_visit_user'),
    ]

    operations = [
        migrations.RunPython(populate_visit_users, reverse_populate),
    ]
