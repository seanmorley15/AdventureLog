from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from procrastinate.contrib.django import app
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.exceptions import APIError

from .models import BackgroundJob
from .serializers import BackgroundJobSerializer

RECENT_JOBS = 50


class BackgroundJobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Exports, imports and PDFs that run in the background."""

    openapi_tags = ['Jobs']
    serializer_class = BackgroundJobSerializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # building the schema: there is no user
            return BackgroundJob.objects.none()
        return BackgroundJob.objects.filter(user=self.request.user)

    @extend_schema(responses=BackgroundJobSerializer(many=True))
    def list(self, request, *args, **kwargs):
        """
        List your jobs

        The 50 most recent, newest first.
        """
        jobs = self.get_queryset()[:RECENT_JOBS]
        return Response(self.get_serializer(jobs, many=True).data)

    @extend_schema(responses=BackgroundJobSerializer)
    def retrieve(self, request, *args, **kwargs):
        """
        Get a job

        Poll this until `status` is `succeeded`, `failed` or `cancelled`. A succeeded job has a
        `result` summary and, for exports, a `download_url`.
        """
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        responses={
            (200, 'application/octet-stream'): OpenApiResponse(response=bytes, description='The file the job made.'),
            404: OpenApiResponse(description='No such job, or it has no file.'),
            410: OpenApiResponse(description='The file expired and was deleted (`job_expired`).'),
        },
    )
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download a job's file

        Only the owner can. The file is deleted when `expires_at` passes.
        """
        job = self.get_object()
        if not job.result_file:
            if job.expires_at is not None:
                raise APIError('This file has expired. Start the export again.', code='job_expired', status=410)
            raise APIError('This job has no file.', code='not_found', status=404)
        if not job.has_downloadable_result:
            raise APIError('This file has expired. Start the export again.', code='job_expired', status=410)
        try:
            handle = default_storage.open(job.result_file, 'rb')
        except FileNotFoundError:
            raise APIError('This file has expired. Start the export again.', code='job_expired', status=410)
        return FileResponse(
            handle, as_attachment=True, filename=job.result_filename or 'download',
            content_type=job.result_content_type or 'application/octet-stream',
        )

    @extend_schema(
        responses={
            204: OpenApiResponse(description='The job was cancelled, or removed with its files.'),
            409: OpenApiResponse(description='The job is running and cannot be stopped (`job_running`).'),
        },
    )
    def destroy(self, request, *args, **kwargs):
        """
        Cancel or remove a job

        A job that has not started is cancelled. A finished job is removed together with its
        file. A running job cannot be stopped.
        """
        job = self.get_object()
        with transaction.atomic():
            job = BackgroundJob.objects.select_for_update().get(pk=job.pk)
            if job.status == BackgroundJob.Status.RUNNING:
                raise APIError('The job is running. Try again when it has finished.', code='job_running', status=status.HTTP_409_CONFLICT)
            if job.status == BackgroundJob.Status.QUEUED and job.queue_job_id:
                app.job_manager.cancel_job_by_id(job.queue_job_id)
            job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
