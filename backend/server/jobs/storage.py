"""Files of background jobs: the upload a worker reads and the result a user downloads."""

import logging
import shutil
import tempfile
from contextlib import contextmanager
from datetime import timedelta

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.text import get_valid_filename

from .models import BackgroundJob

logger = logging.getLogger(__name__)

COPY_CHUNK = 1024 * 1024


def job_dir(user_id, job_id):
    return f'jobs/{user_id}/{job_id}'


def stage_upload(user_id, job_id, upload):
    """Save an uploaded file where the worker can read it. Returns its storage name."""
    return default_storage.save(f'{job_dir(user_id, job_id)}/input.zip', upload)


@contextmanager
def open_input(job):
    """The staged upload as a local seekable file (a zip reader needs to seek)."""
    with default_storage.open(job.input_file, 'rb') as source, tempfile.TemporaryFile() as local:
        shutil.copyfileobj(source, local, COPY_CHUNK)
        local.seek(0)
        yield local


def save_result_file(job, content, filename, content_type):
    """
    Store the file a job produced and make it downloadable until the job's result expires.

    ``content`` is bytes or an open binary file (a spooled temp file keeps big archives out of memory).
    """
    safe_name = get_valid_filename(filename) or 'result'
    wrapped = ContentFile(content) if isinstance(content, (bytes, bytearray)) else File(content)
    name = default_storage.save(f'{job_dir(job.user_id, job.id)}/result/{safe_name}', wrapped)
    expires_at = timezone.now() + timedelta(hours=settings.JOB_RESULT_TTL_HOURS)
    BackgroundJob.objects.filter(pk=job.pk).update(
        result_file=name, result_filename=safe_name, result_content_type=content_type, expires_at=expires_at
    )
    job.result_file, job.result_filename, job.result_content_type, job.expires_at = name, safe_name, content_type, expires_at
    return name


def _delete(name):
    if not name:
        return
    try:
        default_storage.delete(name)
    except Exception:
        logger.exception('Could not delete job file %s', name)


def delete_input_file(job):
    _delete(job.input_file)
    BackgroundJob.objects.filter(pk=job.pk).update(input_file='')
    job.input_file = ''


def delete_result_file(job):
    _delete(job.result_file)
    BackgroundJob.objects.filter(pk=job.pk).update(result_file='')
    job.result_file = ''


def delete_names(*names):
    """Delete stored files by name (the job row they belonged to is gone)."""
    for name in names:
        _delete(name)
