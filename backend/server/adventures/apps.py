from django.apps import AppConfig

class AdventuresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adventures'
    
    def ready(self):
        import adventures.signals  # Import signals when the app is ready