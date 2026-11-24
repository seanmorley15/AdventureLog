from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # Ensure signal handlers are registered
        import users.signals  # noqa: F401
        # Registers the API key scheme with drf-spectacular.
        import users.schema  # noqa: F401

