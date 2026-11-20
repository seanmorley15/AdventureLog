"""
Declare a user-facing job and start it.

    @job_task('account_export')
    def export_account(job):
        ...                      # read job.user / job.params, write with save_result_file
        return {'size': 123}     # the summary the client sees

    start_job(user, 'account_export')

``job_task`` registers the function as a Procrastinate task that runs it with the job row and
records how it went. ``start_job`` creates the row and queues the task in one transaction.
"""

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from procrastinate.contrib.django import app

from core.errors import ServiceError

from .models import BackgroundJob
from .storage import delete_input_file, stage_upload

logger = logging.getLogger(__name__)

_FUNCTIONS = {}
_TASKS = {}
_NEEDS_INPUT = set()


def job_task(kind, queue='heavy', needs_input=False):
    """
    Register ``func(job)`` as the function that runs jobs of ``kind``.

    ``needs_input`` marks jobs that read the file the user uploaded (``open_input``).
    """

    def decorator(func):
        if kind in _FUNCTIONS:
            raise RuntimeError(f'The job kind {kind!r} is registered twice.')

        # The task takes only the job's id: its inputs live in the job row.
        @app.task(name=f'jobs.run.{kind}', queue=queue)
        def run(job_id):
            execute_job(job_id)

        _FUNCTIONS[kind] = func
        _TASKS[kind] = run
        if needs_input:
            _NEEDS_INPUT.add(kind)
        return func

    return decorator


def registered_kinds():
    return sorted(_FUNCTIONS)


def execute_job(job_id):
    """
    Run the function behind a job row and record the outcome.

    A refusal the user can act on (``ServiceError``: a damaged backup, a full quota) marks the job
    failed with its message and does not fail the queue task. Anything else is recorded with a
    generic message, then re-raised so the queue shows the task as failed with the traceback.
    """
    job = BackgroundJob.objects.filter(pk=job_id).first()
    if job is None or job.status == BackgroundJob.Status.CANCELLED:
        return

    BackgroundJob.objects.filter(pk=job.pk).update(
        status=BackgroundJob.Status.RUNNING, started_at=timezone.now(), finished_at=None, error='', error_code=''
    )
    job.refresh_from_db()

    if job.kind in _NEEDS_INPUT and not job.input_file:
        _finish(
            job, BackgroundJob.Status.FAILED, error_code='input_missing',
            error='The uploaded file is no longer available. Upload it again.',
        )
        return

    try:
        result = _FUNCTIONS[job.kind](job)
    except ServiceError as exc:
        _finish(job, BackgroundJob.Status.FAILED, error=exc.message, error_code=exc.code, result=exc.extra or None)
        return
    except Exception:
        logger.exception('Background job %s (%s) failed', job.pk, job.kind)
        _finish(job, BackgroundJob.Status.FAILED, error='The job failed. Please try again later.', error_code='server_error')
        raise

    _finish(job, BackgroundJob.Status.SUCCEEDED, result=result if isinstance(result, dict) else None)
    # The staged upload has been used. A failed job keeps it so an admin can retry.
    delete_input_file(job)


def _finish(job, status, **fields):
    BackgroundJob.objects.filter(pk=job.pk).update(status=status, finished_at=timezone.now(), **fields)


def start_job(user, kind, params=None, upload=None):
    """
    Create a job for ``user`` and queue it. Returns the ``BackgroundJob``.

    ``upload`` is a file from the request. It is saved to storage first because the worker is
    another process. The row and the queue entry are created in one transaction, so a job is
    never queued without its row or the other way round. With ``JOBS_RUN_INLINE`` the job runs
    before this returns.
    """
    if kind not in _TASKS:
        raise ValueError(f'No job task is registered for {kind!r}.')

    job_id = uuid.uuid4()
    input_name = stage_upload(user.pk, job_id, upload) if upload is not None else ''
    try:
        with transaction.atomic():
            job = BackgroundJob.objects.create(id=job_id, user=user, kind=kind, params=params or {}, input_file=input_name)
            if not settings.JOBS_RUN_INLINE:
                job.queue_job_id = _TASKS[kind].defer(job_id=str(job.id))
                job.save(update_fields=['queue_job_id'])
    except Exception:
        if input_name:
            delete_input_file(BackgroundJob(id=job_id, user=user, input_file=input_name))
        raise

    if settings.JOBS_RUN_INLINE:
        try:
            execute_job(job.id)
        except Exception:  # already recorded on the row; the caller reads the outcome from it
            pass
        job.refresh_from_db()
    return job


def requeue_job(job):
    """Queue a failed job again with the same inputs (the admin's retry)."""
    with transaction.atomic():
        BackgroundJob.objects.filter(pk=job.pk).update(
            status=BackgroundJob.Status.QUEUED, error='', error_code='', started_at=None, finished_at=None
        )
        job.queue_job_id = _TASKS[job.kind].defer(job_id=str(job.id))
        job.save(update_fields=['queue_job_id'])
