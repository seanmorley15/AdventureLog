from datetime import timedelta

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion


def create_subscriptions(apps, schema_editor):
    user_model_label, user_model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_model_label, user_model_name)
    Subscription = apps.get_model("billing", "Subscription")

    if getattr(settings, "CLOUD_MODE", False):
        trial_ends_at = timezone.now() + timedelta(days=getattr(settings, "CLOUD_TRIAL_DAYS", 30))
        defaults = {
            "status": "trial",
            "trial_ends_at": trial_ends_at,
        }
    else:
        defaults = {"status": "active", "trial_ends_at": None}

    for user in User.objects.all():
        Subscription.objects.get_or_create(user=user, defaults=defaults)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stripe_customer_id", models.CharField(blank=True, max_length=255)),
                ("stripe_subscription_id", models.CharField(blank=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("trial", "Trial"),
                            ("active", "Active"),
                            ("canceled", "Canceled"),
                            ("past_due", "Past Due"),
                        ],
                        default="trial",
                        max_length=50,
                    ),
                ),
                ("trial_ends_at", models.DateTimeField(blank=True, null=True)),
                ("current_period_ends_at", models.DateTimeField(blank=True, null=True)),
                ("cancel_at_period_end", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.RunPython(create_subscriptions, migrations.RunPython.noop),
    ]
