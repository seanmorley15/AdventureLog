import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler import util
from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)

def run_worldtravel_seed():
    logger.info("Starting worldtravel-seed job")
    try:
        call_command('worldtravel-seed', '--force')
        logger.info("worldtravel-seed job completed successfully")
    except Exception as e:
        logger.error(f"Error in worldtravel-seed job: {str(e)}")

@util.close_old_connections
def start_scheduler():
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        run_worldtravel_seed,
        trigger="interval",
        minutes=3,
        id="worldtravel_seed",
        max_instances=1,
        replace_existing=True,
    )

    logger.info("Starting scheduler...")
    scheduler.start()