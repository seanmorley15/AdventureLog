import logging
import zipfile

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from adventures.serializers.backup import CollectionImportSerializer, CollectionPdfOptionsSerializer
from adventures.serializers.collection_detail import CollectionImportResultSerializer
from adventures.services.backup import (
    BackupError,
    export_collection_archive,
    restore_collection_archive,
)
from core.exceptions import APIError
from jobs.registry import start_job
from jobs.responses import accepted, wants_async
from jobs.serializers import BackgroundJobSerializer
from rest_framework.exceptions import NotAuthenticated
from core.serializers import validated
from adventures.access.audience import audience_for_request
from django.contrib.auth import get_user_model
from adventures.services.exports.pdf import (
    PdfOptions,
    build_collection_pdf,
    get_collection_for_pdf,
    pdf_filename_for_collection,
)
from adventures.services.exports.share_image import (
    build_share_image,
    get_collection_for_share,
    resolve_share_page_url,
    share_image_filename,
)

User = get_user_model()
logger = logging.getLogger(__name__)



ASPECT_PARAMETER = OpenApiParameter(
    'aspect', str, OpenApiParameter.PATH, enum=['square', 'story', 'landscape'],
    description='`square` (1080×1080), `story` (1080×1920) or `landscape` (1200×630).',
)
DOWNLOAD_PARAMETER = OpenApiParameter(
    'download', OpenApiTypes.BOOL, description='Send as an attachment instead of inline.'
)


class ExportActionsMixin:
    """Downloading a collection (PDF, share image, zip) and importing one from a zip."""

    @extend_schema(
        methods=['GET'],
        operation_id='collections_pdf',
        parameters=[CollectionPdfOptionsSerializer],
        responses={(200, 'application/pdf'): OpenApiResponse(response=bytes, description='The PDF.')},
    )
    @extend_schema(
        methods=['POST'],
        operation_id='collections_pdf_start',
        request=CollectionPdfOptionsSerializer,
        responses={202: OpenApiResponse(BackgroundJobSerializer, description='The PDF is being made; see `Location`.')},
    )
    @action(detail=True, methods=['get', 'post'], url_path='pdf')
    def pdf(self, request, pk=None):
        """
        Download as PDF

        A trip becomes a **Trip Book** to travel with: a cover, an overview map, bookings and
        costs, then a page for each day with its own map and timeline. A folder becomes a
        **Field Guide** workbook: an overview map, a checklist, and an entry for each place with
        boxes to tick and lines to write on. Members get the whole plan; public readers get what
        the story shows.

        Choose the page size, photos and write-in space with the options below (query parameters
        on `GET`, a JSON body on `POST`).

        `POST` (signed in) makes the PDF in the background and answers `202` with a job. Poll
        `GET /api/jobs/{id}/` and download the file from its `download_url`.
        """
        collection = self.get_object()
        audience = audience_for_request(request, collection)
        if request.method == 'POST':
            if not request.user.is_authenticated:
                raise NotAuthenticated()
            options = validated(CollectionPdfOptionsSerializer, request.data)
            job = start_job(
                request.user, 'collection_pdf',
                params={'collection_id': str(collection.id), 'story': audience.is_public_reader, 'options': dict(options)},
            )
            return accepted(job)
        options = PdfOptions.from_params(
            validated(CollectionPdfOptionsSerializer, request.query_params),
            user=request.user, collection=collection,
        )
        try:
            collection = get_collection_for_pdf(collection.id)
            pdf_bytes = build_collection_pdf(collection, story=audience.is_public_reader, options=options)
        except Exception:
            logger.exception('Failed to generate PDF for collection %s', collection.id)
            raise APIError('The PDF could not be made. Please try again later.', code='server_error', status=500)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename_for_collection(collection)}"'
        return response

    @extend_schema(
        parameters=[ASPECT_PARAMETER, DOWNLOAD_PARAMETER],
        responses={(200, 'image/png'): OpenApiResponse(response=bytes, description='A PNG image.')},
    )
    @action(detail=True, methods=['get'], url_path=r'share-image/(?P<aspect>square|story|landscape)')
    def share_image(self, request, pk=None, aspect=None):
        """
        Get a share card

        A branded PNG for social media with the cover photo, name, dates and a link. Public
        collections can be fetched without signing in.
        """
        collection = self.get_object()
        try:
            collection = get_collection_for_share(collection.id)
            page_url = resolve_share_page_url(request, f'/collections/{collection.id}')
            png_bytes = build_share_image(collection, aspect, page_url)
        except Exception:
            logger.exception('Failed to generate share image for collection %s', collection.id)
            raise APIError('The share image could not be made. Please try again later.', code='server_error', status=500)

        download = str(request.query_params.get('download', '')).lower() in ('1', 'true', 'yes')
        response = HttpResponse(png_bytes, content_type='image/png')
        disposition = 'attachment' if download else 'inline'
        response['Content-Disposition'] = f'{disposition}; filename="{share_image_filename(collection, aspect)}"'
        return response

    @extend_schema(
        methods=['GET'],
        operation_id='collections_archive',
        responses={(200, 'application/zip'): OpenApiResponse(response=bytes, description='The archive.')},
    )
    @extend_schema(
        methods=['POST'],
        operation_id='collections_archive_start',
        request=None,
        responses={202: OpenApiResponse(BackgroundJobSerializer, description='The export started; see `Location`.')},
    )
    @action(detail=True, methods=['get', 'post'], url_path='archive')
    def archive(self, request, pk=None):
        """
        Download as a zip archive

        Owner only. The collection and everything in it, with media, for
        `POST /api/collections/import/` on this or another server.

        `POST` builds it in the background and answers `202` with a job. Poll
        `GET /api/jobs/{id}/` and download the file from its `download_url`.
        """
        if request.method == 'POST':
            return accepted(start_job(request.user, 'collection_archive', params={'collection_id': str(self.get_object().id)}))
        archive = export_collection_archive(request.user, self.get_object())
        response = HttpResponse(archive.content, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{archive.filename}"'
        return response

    @extend_schema(
        request={'multipart/form-data': CollectionImportSerializer},
        responses={
            201: CollectionImportResultSerializer,
            202: OpenApiResponse(BackgroundJobSerializer, description='With `Prefer: respond-async`: the import started.'),
            400: OpenApiResponse(description='Not a valid collection archive (`invalid_backup`).'),
            413: OpenApiResponse(description='The media would exceed your storage (`media_quota_exceeded`).'),
        },
    )
    @action(detail=False, methods=['post'], url_path='import', parser_classes=[MultiPartParser])
    def import_collection(self, request):
        """
        Import a collection

        Adds the collection in an archive from `GET /api/collections/{id}/archive/` to your
        account, next to what you have. `existing_locations` decides what happens to places
        you already have.

        Send `Prefer: respond-async` to run it in the background: the answer is `202` with a job,
        and its `result` has the new `collection_id` and a `summary` when it succeeds.
        """
        params = validated(CollectionImportSerializer, request.data)
        if wants_async(request):
            if not zipfile.is_zipfile(params['file']):
                raise BackupError('The file is not a zip archive.')
            params['file'].seek(0)
            return accepted(
                start_job(
                    request.user, 'collection_import',
                    params={'existing_locations': params['existing_locations']}, upload=params['file'],
                )
            )
        try:
            result = restore_collection_archive(
                params['file'], request.user, existing_locations=params['existing_locations']
            )
        except BackupError:
            raise
        except zipfile.BadZipFile:
            raise BackupError('The file is not a zip archive.')
        except Exception as exc:
            # A damaged or hand-edited file fails part-way; the import is rolled back.
            logger.exception('Collection import failed')
            raise BackupError('The file could not be imported. It may be damaged.') from exc
        data = self.get_serializer(result.collections[0]).data
        data['import_summary'] = result.summary
        return Response(data, status=status.HTTP_201_CREATED)
