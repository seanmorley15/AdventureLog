from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
import time
from adventures.scheduler import start_scheduler
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Starts the APScheduler'

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database...')
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections['default']
            except OperationalError:
                self.stdout.write('Database unavailable, waiting 1 second...')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Database available!'))
        
        start_scheduler()
        self.stdout.write(self.style.SUCCESS('Scheduler started successfully'))

        # Keep the command running
        while True:
            time.sleep(60)