# import logging
# from apscheduler.schedulers.background import BackgroundScheduler
# from django_apscheduler.jobstores import DjangoJobStore
# from django_apscheduler import util
# from django.conf import settings
# from django.core.management import call_command
# from django.db import connections
# from django.db.utils import OperationalError
# import time

# logger = logging.getLogger(__name__)

# def run_worldtravel_seed():
#     logger.info("Starting worldtravel-seed job")
#     try:
#         call_command('worldtravel-seed', '--force')
#         logger.info("worldtravel-seed job completed successfully")
#     except Exception as e:
#         logger.error(f"Error in worldtravel-seed job: {str(e)}")

# def database_ready():
#     db_conn = connections['default']
#     try:
#         db_conn.cursor()
#     except OperationalError:
#         return False
#     else:
#         return True

# @util.close_old_connections
# def start_scheduler():
#     scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
#     scheduler.add_jobstore(DjangoJobStore(), "default")

#     # Wait for the database to be ready
#     retry_count = 0
#     max_retries = 2  # Set to 2 attempts
#     while not database_ready():
#         if retry_count >= max_retries:
#             logger.error("Database not available after 2 attempts. Scheduler not started.")
#             return None
#         logger.info("Database not ready. Waiting before retry...")
#         time.sleep(2)  # Wait for 2 seconds before retrying
#         retry_count += 1

#     scheduler.add_job(
#         run_worldtravel_seed,
#         trigger="interval",
#         hours=24,
#         id="worldtravel_seed",
#         max_instances=1,
#         replace_existing=True,
#     )
#     logger.info("Starting scheduler...")
#     scheduler.start()
#     return scheduler