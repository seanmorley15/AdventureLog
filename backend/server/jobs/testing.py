"""Run queued jobs in tests, in the test's own thread and transaction (no worker process)."""

from django.db import connection
from procrastinate.contrib.django import app
from procrastinate.contrib.django.models import ProcrastinateJob


def run_pending_jobs(task_name=None):
    """
    Run every job in the queue (optionally only those of one task) and return their task names.

    Jobs are queued for real into the test database, so a test also proves that a view queued
    the right task with the right arguments. A job queued while running another runs too.
    """
    ran = []
    while True:
        pending = ProcrastinateJob.objects.filter(status='todo').order_by('id')
        if task_name:
            pending = pending.filter(task_name=task_name)
        job = pending.first()
        if job is None:
            return ran
        # Marked done before it runs, so a task that fails is not run again by this loop. The queue's
        # table is read-only through Django's models, hence the SQL.
        with connection.cursor() as cursor:
            cursor.execute("UPDATE procrastinate_jobs SET status = 'succeeded' WHERE id = %s", [job.pk])
        app.tasks[job.task_name].func(**job.args)
        ran.append(job.task_name)


def queued_jobs(task_name=None):
    """The jobs waiting in the queue, for asserting what a view queued."""
    jobs = ProcrastinateJob.objects.filter(status='todo').order_by('id')
    return jobs.filter(task_name=task_name) if task_name else jobs


def discard_pending_jobs():
    """Empty the queue without running anything, to start a test step from a clean slate."""
    with connection.cursor() as cursor:
        cursor.execute("UPDATE procrastinate_jobs SET status = 'succeeded' WHERE status = 'todo'")
