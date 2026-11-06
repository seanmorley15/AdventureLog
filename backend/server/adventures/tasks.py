"""
Background tasks of the adventures app. The worker imports this module.

Small tasks answer something that happened (a place was saved, a comment mentioned someone, a
file lost its row) and retry on their own. The scheduled task replaces a cron job. The tasks
behind exports and imports are in the second half of the file; they report to a
``jobs.BackgroundJob`` the user can watch.
"""

import logging
import zipfile
from smtplib import SMTPException

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from procrastinate import RetryStrategy
from procrastinate.contrib.django import app

from adventures.services.backup import (
    LINK_EXISTING_LOCATIONS,
    BackupError,
    BackupExporter,
    account_backup_filename,
    build_archive_file,
    collection_archive_filename,
    restore_account_backup,
    restore_collection_archive,
)
from core.errors import ServiceError
from jobs.registry import job_task
from jobs.storage import open_input, save_result_file

logger = logging.getLogger(__name__)

# Small tasks run before the long ones when the worker has a free slot.
SMALL_TASK_PRIORITY = 10


@app.task(
    name='adventures.geocode_location',
    queue='default',
    priority=SMALL_TASK_PRIORITY,
    # Nominatim rate limits and timeouts clear up: wait 60s, then 90s, 120s, 150s, then give up.
    retry=RetryStrategy(max_attempts=5, wait=30, linear_wait=30),
)
def geocode_location(location_id):
    """Fill in a place's country, region and city from its coordinates."""
    from adventures.services.geocoding.assignment import geocode_and_assign_location

    geocode_and_assign_location(location_id, raise_if_unavailable=True)


@app.task(
    name='adventures.send_mention_email',
    queue='default',
    priority=SMALL_TASK_PRIORITY,
    retry=RetryStrategy(max_attempts=5, wait=60, linear_wait=60, retry_exceptions={SMTPException, OSError}),
)
def send_mention_email_task(comment_id, user_id, page_url=None):
    """E-mail one member a comment mentioned. A mail server that is down is retried."""
    from adventures.models import CollectionComment
    from adventures.services.discussion import send_mention_email

    comment = CollectionComment.objects.select_related('collection').filter(pk=comment_id).first()
    user = get_user_model().objects.filter(pk=user_id).first()
    if comment is None or user is None:
        return  # deleted since it was queued
    send_mention_email(comment, user, page_url, fail_silently=False)


@app.task(
    name='adventures.delete_stored_file',
    queue='default',
    priority=SMALL_TASK_PRIORITY,
    retry=RetryStrategy(max_attempts=3, wait=60),
)
def delete_stored_file(model_label, field_name, name):
    """Delete a stored file unless another row of the model still uses it (a duplicated place shares one)."""
    model = apps.get_model(model_label)
    if model.objects.filter(**{field_name: name}).exists():
        return
    model._meta.get_field(field_name).storage.delete(name)


# Replaces the nightly cron job. `lock` keeps two runs from overlapping; `queueing_lock` keeps one waiting.
@app.periodic(cron='0 0 * * *')
@app.task(name='adventures.sync_visited_regions', queueing_lock='adventures.sync_visited_regions', lock='adventures.sync_visited_regions')
def sync_visited_regions_nightly(timestamp):
    """Midnight UTC: mark the regions and cities of every user's visited places as visited."""
    call_command('sync_visited_regions')


# ---------------------------------------------------------------------------
# Exports and imports. Each runs for a ``jobs.BackgroundJob`` and reports to it.
# The request has already checked who may do this; a task re-reads everything by id.
# ---------------------------------------------------------------------------

ZIP = 'application/zip'


@job_task('account_export')
def account_export(job):
    """Everything the user owns, as one zip."""
    with build_archive_file(BackupExporter(job.user)) as archive:
        save_result_file(job, archive, account_backup_filename(job.user), ZIP)


@job_task('collection_archive')
def collection_archive_export(job):
    """One collection and what belongs to it, as a zip."""
    from adventures.models import Collection

    collection = Collection.objects.get(pk=job.params['collection_id'])
    with build_archive_file(BackupExporter(job.user, collection)) as archive:
        save_result_file(job, archive, collection_archive_filename(collection), ZIP)


@job_task('collection_pdf')
def collection_pdf_export(job):
    """A printable day-by-day itinerary."""
    from adventures.services.exports.pdf import build_collection_pdf, get_collection_for_pdf, pdf_filename_for_collection

    collection = get_collection_for_pdf(job.params['collection_id'])
    pdf = build_collection_pdf(collection, story=bool(job.params.get('story')))
    save_result_file(job, pdf, pdf_filename_for_collection(collection), 'application/pdf')


@job_task('account_restore', needs_input=True)
def account_restore(job):
    """Replace the user's account with a backup. All or nothing: a failure rolls everything back."""
    with open_input(job) as upload:
        try:
            summary = restore_account_backup(upload, job.user)
        except zipfile.BadZipFile:
            raise BackupError('The file is not a zip archive.')
        except ServiceError:
            raise
        except Exception as exc:
            # A damaged or hand-edited file fails part-way.
            logger.exception('Backup import failed')
            raise BackupError('The file could not be imported. It may be damaged.') from exc
    return {'summary': summary}


@job_task('collection_import', needs_input=True)
def collection_import(job):
    """Add the collection in an archive to the user's account."""
    with open_input(job) as upload:
        try:
            result = restore_collection_archive(
                upload, job.user, existing_locations=job.params.get('existing_locations', LINK_EXISTING_LOCATIONS)
            )
        except zipfile.BadZipFile:
            raise BackupError('The file is not a zip archive.')
        except ServiceError:
            raise
        except Exception as exc:
            logger.exception('Collection import failed')
            raise BackupError('The file could not be imported. It may be damaged.') from exc
    return {'collection_id': str(result.collections[0].pk), 'summary': result.summary}


@job_task('image_import')
def image_import(job):
    """Download images from web addresses and attach them to a record."""
    from adventures.services.images.fetch import import_remote_images_for_object
    from adventures.views.images import ContentImageViewSet

    params = job.params
    model = ContentImageViewSet.content_object_models[params['content_type']]
    content_object = model.objects.get(id=params['object_id'])
    owner = ContentImageViewSet()._content_owner(content_object, job.user)

    summary = import_remote_images_for_object(
        content_object,
        params['urls'],
        owner=owner,
        max_workers=min(5, len(params['urls'])),
        explicit_source=params.get('source'),
    )
    if not summary['created_images']:
        raise ServiceError(
            'None of the images could be imported.', code='import_failed', extra={'results': summary['results']}
        )
    return {
        'created_ids': [str(image.pk) for image in summary['created_images']],
        'results': summary['results'],
        'created_count': summary['created_count'],
        'requested_count': summary['requested_count'],
    }
