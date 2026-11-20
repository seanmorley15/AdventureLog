"""The two job lists in the admin and their actions."""

from django.test import TestCase
from django.urls import reverse
from procrastinate.contrib.django.models import ProcrastinateJob

from core.testing import make_user
from jobs.models import BackgroundJob
from jobs.registry import start_job
from jobs.testing import queued_jobs, run_pending_jobs
from jobs.tests import test_registry  # noqa: F401  (registers the test_* job kinds)


class JobAdminTests(TestCase):
    def setUp(self):
        self.admin = make_user('job-admin', is_staff=True, is_superuser=True)
        self.client.force_login(self.admin)

    def test_both_lists_open(self):
        start_job(self.admin, 'test_ok')

        mine = self.client.get(reverse('admin:jobs_backgroundjob_changelist'))
        queue = self.client.get(reverse('admin:procrastinate_procrastinatejob_changelist'))

        self.assertEqual(mine.status_code, 200)
        self.assertContains(mine, 'test_ok')
        self.assertEqual(queue.status_code, 200)
        self.assertContains(queue, 'j.r.test_ok')  # the list shortens module names

    def test_a_job_page_opens(self):
        job = start_job(self.admin, 'test_ok')

        response = self.client.get(reverse('admin:jobs_backgroundjob_change', args=[job.pk]))

        self.assertEqual(response.status_code, 200)

    def test_retry_queues_a_failed_job_again(self):
        job = start_job(self.admin, 'test_refuse')
        run_pending_jobs()
        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundJob.Status.FAILED)

        response = self.client.post(
            reverse('admin:jobs_backgroundjob_changelist'),
            {'action': 'retry_jobs', '_selected_action': [str(job.pk)]},
        )

        self.assertEqual(response.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundJob.Status.QUEUED)
        self.assertEqual(queued_jobs('jobs.run.test_refuse').count(), 1)

    def test_run_again_queues_the_same_task_with_the_same_arguments(self):
        job = start_job(self.admin, 'test_ok')
        queue_job = ProcrastinateJob.objects.get(pk=job.queue_job_id)

        self.client.post(
            reverse('admin:procrastinate_procrastinatejob_changelist'),
            {'action': 'run_again', '_selected_action': [str(queue_job.pk)]},
        )

        self.assertEqual(queued_jobs('jobs.run.test_ok').count(), 2)
