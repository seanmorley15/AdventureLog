from django.db import migrations


def backfill_email_addresses(apps, schema_editor):
    """
    Accounts given an email in the Django admin had no allauth EmailAddress row, so
    Settings -> Emails showed none and re-adding it failed as a duplicate. Give each account
    with an email and no rows at all an unverified primary row for it.
    """
    User = apps.get_model('users', 'CustomUser')
    EmailAddress = apps.get_model('account', 'EmailAddress')
    with_rows = EmailAddress.objects.values_list('user_id', flat=True)
    missing = (
        User.objects.exclude(email__isnull=True)
        .exclude(email='')
        .exclude(pk__in=with_rows)
        .only('pk', 'email')
    )
    EmailAddress.objects.bulk_create(
        [
            EmailAddress(user_id=user.pk, email=user.email.strip(), primary=True, verified=False)
            for user in missing.iterator()
            if user.email.strip()
        ],
        batch_size=500,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_default_currency_all_circulating'),
        ('account', '0009_emailaddress_unique_primary_email'),
    ]

    operations = [
        migrations.RunPython(backfill_email_addresses, migrations.RunPython.noop),
    ]
