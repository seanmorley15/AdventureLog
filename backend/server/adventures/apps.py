from django.apps import AppConfig
from django.conf import settings

class AdventuresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adventures'

    def ready(self):
        if settings.SCHEDULER_AUTOSTART:
            from django.core.management import call_command
            import threading
            threading.Thread(target=call_command, args=('start_scheduler',)).start()