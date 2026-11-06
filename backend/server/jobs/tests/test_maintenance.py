"""The hourly clean-up of finished jobs."""

from datetime import timedelta

from django.core.files.storage import default_storage
from django.test import TestCase
from django.utils import timezone

from core.testing import make_user
from jobs.maintenance import prune_jobs
from jobs.models import BackgroundJob
from jobs.registry import start_job
from jobs.storage import save_result_file
from jobs.tests import test_registry  # noqa: F401  (registers the test_* job kinds)


class PruneJobsTests(TestCase):
    def setUp(self):
        self.user = make_user('pruned')

    def job_with_result(self, **fields):
        job = start_job(self.user, 'test_ok')
        save_result_file(job, b'data', 'data.bin', 'application/octet-stream')
        BackgroundJob.objects.filter(pk=job.pk).update(status=BackgroundJob.Status.SUCCEEDED, **fields)
        job.refresh_from_db()
        return job

    def test_an_expired_result_is_deleted_and_a_fresh_one_kept(self):
        now = timezone.now()
        old = self.job_with_result(expires_at=now - timedelta(minutes=1), finished_at=now)
        fresh = self.job_with_result(expires_at=now + timedelta(hours=1), finished_at=now)

        counts = prune_jobs(now)

        self.assertEqual(counts['results'], 1)
        old.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(old.result_file, '')
        self.assertFalse(old.has_downloadable_result)
        self.assertTrue(default_storage.exists(fresh.result_file))

    def test_an_old_row_is_deleted_with_its_files(self):
        now = timezone.now()
        job = self.job_with_result(finished_at=now - timedelta(days=8), expires_at=now - timedelta(days=7))
        name = job.result_file
        recent = self.job_with_result(finished_at=now - timedelta(days=1), expires_at=now + timedelta(hours=1))

        with self.captureOnCommitCallbacks(execute=True):
            prune_jobs(now)

        self.assertFalse(BackgroundJob.objects.filter(pk=job.pk).exists())
        self.assertTrue(BackgroundJob.objects.filter(pk=recent.pk).exists())
        self.assertFalse(default_storage.exists(name))

    def test_an_upload_left_by_a_failed_job_is_deleted_after_a_day(self):
        now = timezone.now()
        job = start_job(self.user, 'test_ok')
        BackgroundJob.objects.filter(pk=job.pk).update(
            status=BackgroundJob.Status.FAILED, input_file='jobs/x/input.zip', finished_at=now - timedelta(days=2)
        )

        counts = prune_jobs(now)

        self.assertEqual(counts['inputs'], 1)
        job.refresh_from_db()
        self.assertEqual(job.input_file, '')
