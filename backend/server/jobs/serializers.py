from rest_framework import serializers

from .models import BackgroundJob


class BackgroundJobSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField(
        help_text='Where to download the file, once the job has succeeded and until `expires_at`. Otherwise null.'
    )
    filename = serializers.CharField(source='result_filename', read_only=True)

    class Meta:
        model = BackgroundJob
        fields = [
            'id', 'kind', 'status', 'result', 'error', 'error_code', 'filename', 'download_url',
            'created_at', 'started_at', 'finished_at', 'expires_at',
        ]
        read_only_fields = fields

    def get_download_url(self, job) -> str | None:
        return f'/api/jobs/{job.id}/download/' if job.has_downloadable_result else None
