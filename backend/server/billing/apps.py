from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "billing"

    def ready(self):
        import billing.signals  # noqa: F401
