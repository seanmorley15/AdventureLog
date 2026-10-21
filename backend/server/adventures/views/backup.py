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

logger = logging.getLogger(__name__)


class BackupViewSet(viewsets.ViewSet):
    """Download everything the user owns as a zip, or replace it all from one."""

    openapi_tags = ['Backup']

    @extend_schema(
        responses={(200, 'application/zip'): OpenApiResponse(response=bytes, description='The backup file.')},
    )
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export your account

        A zip file with every record you own and their media, in a format that
        `POST /api/backup/import/` restores, also on another server.
        """
        backup = export_account_backup(request.user)
        response = HttpResponse(backup.content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{backup.filename}"'
        return response

    @extend_schema(
        request={'multipart/form-data': BackupImportSerializer},
        responses={
            200: BackupImportResultSerializer,
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
        """
        params = validated(BackupImportSerializer, request.data)
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
