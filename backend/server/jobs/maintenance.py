"""Housekeeping for job rows and files, run hourly by ``jobs.tasks``."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import BackgroundJob
from .storage import delete_input_file, delete_result_file

# A finished job stays in the user's list this long.
KEEP_ROWS_DAYS = 7


def prune_jobs(now=None):
    """Delete expired result files, abandoned uploads and old rows. Returns how many of each."""
    now = now or timezone.now()
    counts = {'results': 0, 'inputs': 0, 'rows': 0}

    for job in BackgroundJob.objects.exclude(result_file='').filter(expires_at__lte=now):
        delete_result_file(job)
        counts['results'] += 1

    # A failed job keeps its upload for an admin retry, as long as a result would stay.
    abandoned = now - timedelta(hours=settings.JOB_RESULT_TTL_HOURS)
    for job in BackgroundJob.objects.exclude(input_file='').filter(finished_at__lte=abandoned):
        delete_input_file(job)
        counts['inputs'] += 1

    # The row's delete signal removes any file still stored.
    for job in BackgroundJob.objects.filter(finished_at__lte=now - timedelta(days=KEEP_ROWS_DAYS)):
        job.delete()
        counts['rows'] += 1

    return counts
