import logging

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adventures.services.backup import BackupError, export_account_backup, restore_account_backup

logger = logging.getLogger(__name__)


class BackupViewSet(viewsets.ViewSet):
    """Download everything the user owns as a zip, or replace it all from one."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def export(self, request):
        backup = export_account_backup(request.user)
        response = HttpResponse(backup.content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{backup.filename}"'
        return response

    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser],
        url_path='import',
        url_name='import',
    )
    def import_data(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        if request.data.get('confirm') != 'yes':
            return Response(
                {'error': 'Confirmation required to proceed with import'}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            summary = restore_account_backup(request.FILES['file'], request.user)
        except BackupError as error:
            return Response({'error': error.message, **error.extra}, status=error.status)
        except Exception:
            logger.error('Import failed', exc_info=True)
            return Response(
                {'error': 'An internal error occurred during import'}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {'success': True, 'message': 'Data imported successfully', 'summary': summary},
            status=status.HTTP_200_OK,
        )
