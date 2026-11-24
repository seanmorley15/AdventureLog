from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'jobs'

    def ready(self):
        from . import signals  # noqa: F401
