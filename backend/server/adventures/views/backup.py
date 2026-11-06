import logging
import zipfile

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from adventures.serializers.backup import BackupImportResultSerializer, BackupImportSerializer
from adventures.services.backup import BackupError, export_account_backup, restore_account_backup
from core.serializers import validated
from jobs.registry import start_job
from jobs.responses import accepted, wants_async
from jobs.serializers import BackgroundJobSerializer

logger = logging.getLogger(__name__)


class BackupViewSet(viewsets.ViewSet):
    """Download everything the user owns as a zip, or replace it all from one."""

    openapi_tags = ['Backup']

    @extend_schema(
        methods=['GET'],
        operation_id='backup_export',
        responses={(200, 'application/zip'): OpenApiResponse(response=bytes, description='The backup file.')},
    )
    @extend_schema(
        methods=['POST'],
        operation_id='backup_export_start',
        request=None,
        responses={202: OpenApiResponse(BackgroundJobSerializer, description='The export started; see `Location`.')},
    )
    @action(detail=False, methods=['get', 'post'])
    def export(self, request):
        """
        Export your account

        A zip file with every record you own and their media, in a format that
        `POST /api/backup/import/` restores, also on another server.

        `POST` starts the export in the background and answers `202` with a job. Poll
        `GET /api/jobs/{id}/` and download the file from its `download_url`. `GET` builds the file
        during the request, which can time out for a large account.
        """
        if request.method == 'POST':
            return accepted(start_job(request.user, 'account_export'))
        backup = export_account_backup(request.user)
        response = HttpResponse(backup.content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{backup.filename}"'
        return response

    @extend_schema(
        request={'multipart/form-data': BackupImportSerializer},
        responses={
            200: BackupImportResultSerializer,
            202: OpenApiResponse(BackgroundJobSerializer, description='With `Prefer: respond-async`: the restore started.'),
            400: OpenApiResponse(description='Not a valid backup (`invalid_backup`) or not confirmed.'),
            413: OpenApiResponse(description='The media in the file would exceed your storage (`media_quota_exceeded`).'),
        },
    )
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser], url_path='import', url_name='import')
    def import_data(self, request):
        """
        Restore your account from a backup

        **Deletes everything in your account**, then loads the backup. Send `confirm=yes`. The
        response counts what was restored.

        Send `Prefer: respond-async` to run it in the background: the answer is `202` with a job,
        and the counts are in the job's `result.summary` when it succeeds. Nothing is deleted if
        the file turns out not to be usable.
        """
        params = validated(BackupImportSerializer, request.data)
        if wants_async(request):
            if not zipfile.is_zipfile(params['file']):
                raise BackupError('The file is not a zip archive.')
            params['file'].seek(0)
            return accepted(start_job(request.user, 'account_restore', upload=params['file']))
        try:
            summary = restore_account_backup(params['file'], request.user)
        except BackupError:
            raise
        except zipfile.BadZipFile:
            raise BackupError('The file is not a zip archive.')
        except Exception as exc:
            # A damaged or hand-edited file fails part-way; the restore is rolled back.
            logger.exception('Backup import failed')
            raise BackupError('The file could not be imported. It may be damaged.') from exc
        return Response({'summary': summary})
