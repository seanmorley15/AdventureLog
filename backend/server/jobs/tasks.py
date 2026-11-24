"""Scheduled maintenance. Imported by the worker, which also runs the schedule."""

import logging

from django.core.management import call_command
from procrastinate import builtin_tasks
from procrastinate.contrib.django import app

from .maintenance import prune_jobs

logger = logging.getLogger(__name__)

# How long a finished job stays in the queue's own table (the admin's "Procrastinate jobs").
QUEUE_HISTORY_HOURS = 24 * 7


@app.periodic(cron='0 * * * *')
@app.task(name='jobs.prune_jobs', queueing_lock='jobs.prune_jobs')
def prune_background_jobs(timestamp):
    """Hourly: delete expired exports, abandoned uploads and old job rows."""
    logger.info('Pruned background jobs: %s', prune_jobs())


@app.periodic(cron='30 4 * * *')
@app.task(name='jobs.remove_old_jobs', queueing_lock='jobs.remove_old_jobs', pass_context=True)
async def remove_old_queue_jobs(context, timestamp):
    """Daily: trim the queue's own history."""
    return await builtin_tasks.remove_old_jobs(
        context, max_hours=QUEUE_HISTORY_HOURS, remove_failed=True, remove_cancelled=True, remove_aborted=True
    )


@app.periodic(cron='*/10 * * * *')
@app.task(name='jobs.retry_stalled_jobs', queueing_lock='jobs.retry_stalled_jobs', pass_context=True)
async def retry_stalled_jobs(context, timestamp):
    """
    Every 10 minutes: queue again the jobs whose worker died (killed, out of memory, a deploy that
    did not wait). A worker that stops sending heartbeats is detected by `stalled_worker_timeout`.
    """
    manager = context.app.job_manager
    for job in await manager.get_stalled_jobs():
        logger.warning('Retrying job %s (%s): its worker stopped', job.id, job.task_name)
        await manager.retry_job(job)


@app.periodic(cron='15 3 * * 0')
@app.task(name='jobs.clearsessions', queueing_lock='jobs.clearsessions', lock='jobs.clearsessions')
def clear_expired_sessions(timestamp):
    """Weekly, Sunday 03:15 UTC: purge expired Django sessions."""
    call_command('clearsessions')
