from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from django.http import HttpResponse
import logging
from adventures.services.backup import (
    LINK_EXISTING_LOCATIONS,
    BackupError,
    export_collection_archive,
    restore_collection_archive,
)
from adventures.access.audience import audience_for_request
from django.contrib.auth import get_user_model
from adventures.services.exports.pdf import (
    build_collection_pdf,
    get_collection_for_pdf,
    pdf_filename_for_collection,
)
from adventures.services.exports.share_image import (
    build_share_image,
    get_collection_for_share,
    resolve_share_page_url,
    share_image_filename,
    valid_aspect,
)

User = get_user_model()
logger = logging.getLogger(__name__)



class ExportActionsMixin:
    """Downloading a collection (PDF, share image, zip) and importing one from a zip."""

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """Export collection as a printable day-by-day itinerary PDF."""
        collection = self.get_object()
        audience = audience_for_request(request, collection)
        try:
            collection = get_collection_for_pdf(collection.id)
            # A public reader gets the story groups. Members get the full plan.
            pdf_bytes = build_collection_pdf(collection, story=audience.is_public_reader)
        except Exception:
            logger.exception('Failed to generate PDF for collection %s', collection.id)
            return Response(
                {'error': 'Failed to generate PDF. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = pdf_filename_for_collection(collection)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(
        detail=True,
        methods=['get'],
        url_path=r'share-image/(?P<aspect>square|story|landscape)',
    )
    def share_image(self, request, pk=None, aspect=None):
        """Generate a branded PNG share card for social media."""
        if not valid_aspect(aspect):
            return Response({'error': 'Invalid aspect ratio.'}, status=status.HTTP_400_BAD_REQUEST)

        collection = self.get_object()
        try:
            collection = get_collection_for_share(collection.id)
            page_url = resolve_share_page_url(request, f'/collections/{collection.id}')
            png_bytes = build_share_image(collection, aspect, page_url)
        except Exception:
            logger.exception('Failed to generate share image for collection %s', collection.id)
            return Response(
                {'error': 'Failed to generate share image. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = share_image_filename(collection, aspect)
        disposition = 'attachment' if request.query_params.get('download') else 'inline'
        response = HttpResponse(png_bytes, content_type='image/png')
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'], url_path='export')
    def export_collection(self, request, pk=None):
        """Download a collection and everything in it as a zip file."""
        archive = export_collection_archive(request.user, self.get_object())
        response = HttpResponse(archive.content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{archive.filename}"'
        return response

    @action(detail=False, methods=['post'], url_path='import', parser_classes=[MultiPartParser])
    def import_collection(self, request):
        """
        Add the collection in an exported zip file to the user's account.

        ``existing_locations`` says what to do with a place in the file that the user already
        has: ``link`` (the default) uses theirs, ``create`` makes a new copy.
        """
        upload = request.FILES.get('file')
        if not upload:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = restore_collection_archive(
                upload,
                request.user,
                existing_locations=request.data.get('existing_locations') or LINK_EXISTING_LOCATIONS,
            )
        except BackupError as error:
            return Response({'error': error.message, **error.extra}, status=error.status)
        except Exception:
            logger.error('Collection import failed', exc_info=True)
            return Response(
                {'error': 'An internal error occurred during import'}, status=status.HTTP_400_BAD_REQUEST
            )

        data = self.get_serializer(result.collections[0]).data
        data['import_summary'] = result.summary
        return Response(data, status=status.HTTP_201_CREATED)
