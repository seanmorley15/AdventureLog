from django.apps import AppConfig
from django.conf import settings

class AdventuresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adventures'

    def ready(self):
        if settings.SCHEDULER_AUTOSTART:
            from .scheduler import start_scheduler
            start_scheduler()