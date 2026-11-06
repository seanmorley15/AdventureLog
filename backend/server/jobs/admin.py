from django.contrib import admin, messages
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from procrastinate.contrib.django.admin import ProcrastinateJobAdmin
from procrastinate.contrib.django.models import ProcrastinateJob

from .models import BackgroundJob
from .registry import registered_kinds, requeue_job

STATUS_COLORS = {
    BackgroundJob.Status.QUEUED: '#6b7280',
    BackgroundJob.Status.RUNNING: '#2563eb',
    BackgroundJob.Status.SUCCEEDED: '#16a34a',
    BackgroundJob.Status.FAILED: '#dc2626',
    BackgroundJob.Status.CANCELLED: '#9ca3af',
}


@admin.register(BackgroundJob)
class BackgroundJobAdmin(admin.ModelAdmin):
    """What users started: exports, imports and PDFs. The queue itself is "Procrastinate jobs"."""

    list_display = ('kind', 'user', 'status_badge', 'created_at', 'duration', 'expires_at')
    list_filter = ('status', 'kind', 'created_at')
    search_fields = ('id', 'user__username', 'user__email')
    date_hierarchy = 'created_at'
    raw_id_fields = ('user',)
    actions = ['retry_jobs', 'expire_now']

    fields = (
        'id', 'user', 'kind', 'status', 'error_code', 'error', 'params', 'result',
        'input_file', 'result_file', 'result_filename', 'result_content_type',
        'queue_job', 'created_at', 'started_at', 'finished_at', 'expires_at',
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Status', ordering='status')
    def status_badge(self, job):
        return format_html(
            '<strong style="color:{}">{}</strong>', STATUS_COLORS.get(job.status, '#6b7280'), job.get_status_display()
        )

    @admin.display(description='Took')
    def duration(self, job):
        if not job.started_at or not job.finished_at:
            return '—'
        return f'{(job.finished_at - job.started_at).total_seconds():.1f}s'

    @admin.display(description='Queue job')
    def queue_job(self, job):
        if not job.queue_job_id:
            return '—'
        try:
            url = reverse('admin:procrastinate_procrastinatejob_change', args=[job.queue_job_id])
        except NoReverseMatch:
            return job.queue_job_id
        return format_html('<a href="{}">#{}</a>', url, job.queue_job_id)

    @admin.action(description='Retry failed jobs')
    def retry_jobs(self, request, queryset):
        retried = 0
        for job in queryset.filter(status=BackgroundJob.Status.FAILED, kind__in=registered_kinds()):
            requeue_job(job)
            retried += 1
        self.message_user(request, f'Queued {retried} job(s) again. Only failed jobs can be retried.', messages.INFO)

    @admin.action(description='Delete the results now (files expire)')
    def expire_now(self, request, queryset):
        from django.utils import timezone

        from .storage import delete_result_file

        count = 0
        for job in queryset.exclude(result_file=''):
            delete_result_file(job)
            BackgroundJob.objects.filter(pk=job.pk).update(expires_at=timezone.now())
            count += 1
        self.message_user(request, f'Deleted the file of {count} job(s).', messages.INFO)


# The queue's own admin lists every task (geocoding, mails, the schedule) with its event history
# and already has Retry, Cancel and Abort. This adds running a task again.
admin.site.unregister(ProcrastinateJob)


@admin.register(ProcrastinateJob)
class QueueJobAdmin(ProcrastinateJobAdmin):
    actions = [*ProcrastinateJobAdmin.actions, 'run_again']

    @admin.action(description='Run again (same task and arguments)')
    def run_again(self, request, queryset):
        from procrastinate.contrib.django import app

        for job in queryset:
            app.configure_task(name=job.task_name, queue=job.queue_name).defer(**job.args)
        self.message_user(request, f'Queued {queryset.count()} job(s).', messages.INFO)
