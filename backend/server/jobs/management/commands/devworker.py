"""
Run the job worker for development: it restarts when code changes, like runserver does.

    python manage.py devworker

In a container, the worker is a supervisord program instead (see docker/shared).
"""

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import autoreload


class Command(BaseCommand):
    help = 'Run the background job worker and restart it when the code changes.'

    def handle(self, *args, **options):
        autoreload.run_with_reloader(self._run)

    def _run(self):
        autoreload.raise_last_exception()
        call_command('procrastinate', 'worker', '--concurrency', str(settings.WORKER_CONCURRENCY))
