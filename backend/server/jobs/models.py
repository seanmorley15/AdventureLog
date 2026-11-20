import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class BackgroundJob(models.Model):
    """
    A long-running operation a user started: an export, an import, a PDF.

    The queue itself (what the worker runs, retries and locks) is Procrastinate's table. This row
    is what the user sees: its status, a result summary or an error, and the file to download.
    Files live in the default media storage under ``jobs/<user id>/<job id>/``, which the media
    route never serves; they leave only through ``GET /api/jobs/<id>/download/``.
    """

    class Status(models.TextChoices):
        QUEUED = 'queued'
        RUNNING = 'running'
        SUCCEEDED = 'succeeded'
        FAILED = 'failed'
        CANCELLED = 'cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='background_jobs')
    # Names a function registered with ``jobs.registry.job_task`` (``account_export``, ...).
    kind = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    # Inputs the task needs besides the staged file (ids, options). Never shown to the user.
    params = models.JSONField(default=dict, blank=True)
    # Storage names. Empty when the job has no such file (any more).
    input_file = models.CharField(max_length=512, blank=True)
    result_file = models.CharField(max_length=512, blank=True)
    result_filename = models.CharField(max_length=255, blank=True)
    result_content_type = models.CharField(max_length=100, blank=True)
    # A summary the client shows when the job is done (counts, the id of what was created).
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    # The row in Procrastinate's queue, for the admin to link the two.
    queue_job_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    # When the result file is deleted.
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', '-created_at'])]

    def __str__(self):
        return f'{self.kind} ({self.status})'

    @property
    def is_finished(self):
        return self.status in (self.Status.SUCCEEDED, self.Status.FAILED, self.Status.CANCELLED)

    @property
    def has_downloadable_result(self):
        """A result file that is still stored and has not expired."""
        if not self.result_file:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()
