"""Starting a job, running it, and what is recorded when it succeeds or fails."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings
from procrastinate.contrib.django.models import ProcrastinateJob

from core.errors import ServiceError
from core.testing import make_user
from jobs.models import BackgroundJob
from jobs.registry import execute_job, job_task, start_job
from jobs.storage import save_result_file
from jobs.testing import queued_jobs, run_pending_jobs

CALLS = []


@job_task('test_ok')
def _ok(job):
    CALLS.append(job.pk)
    save_result_file(job, b'hello', 'hello.txt', 'text/plain')
    return {'count': 3}


@job_task('test_refuse')
def _refuse(job):
    raise ServiceError('That file is damaged.', code='invalid_backup', extra={'detail_key': 'x'})


class _Boom(Exception):
    pass


@job_task('test_boom')
def _boom(job):
    raise _Boom('secret internals')


@job_task('test_needs_file', needs_input=True)
def _needs_file(job):
    return {}


class StartJobTests(TestCase):
    def setUp(self):
        CALLS.clear()
        self.user = make_user('starter')

    def test_a_job_row_and_a_queue_entry_are_created_together(self):
        job = start_job(self.user, 'test_ok', params={'a': 1})

        self.assertEqual(job.status, BackgroundJob.Status.QUEUED)
        self.assertEqual(job.params, {'a': 1})
        queued = queued_jobs('jobs.run.test_ok')
        self.assertEqual(queued.count(), 1)
        self.assertEqual(queued[0].args, {'job_id': str(job.id)})
        self.assertEqual(job.queue_job_id, queued[0].id)

    def test_nothing_is_queued_when_the_transaction_rolls_back(self):
        try:
            with transaction.atomic():
                start_job(self.user, 'test_ok')
                raise _Boom()
        except _Boom:
            pass

        self.assertEqual(BackgroundJob.objects.count(), 0)
        self.assertEqual(ProcrastinateJob.objects.count(), 0)

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            start_job(self.user, 'nope')

    @override_settings(JOBS_RUN_INLINE=True)
    def test_inline_mode_runs_the_job_before_returning(self):
        job = start_job(self.user, 'test_ok')

        self.assertEqual(job.status, BackgroundJob.Status.SUCCEEDED)
        self.assertEqual(ProcrastinateJob.objects.count(), 0)

    @override_settings(JOBS_RUN_INLINE=True)
    def test_inline_mode_returns_a_failed_job_instead_of_raising(self):
        job = start_job(self.user, 'test_boom')

        self.assertEqual(job.status, BackgroundJob.Status.FAILED)

    def test_an_upload_is_staged_and_removed_with_the_job(self):
        upload = SimpleUploadedFile('mine.zip', b'PK-data')
        job = start_job(self.user, 'test_needs_file', upload=upload)

        from django.core.files.storage import default_storage

        self.assertTrue(job.input_file.startswith(f'jobs/{self.user.pk}/{job.id}/'))
        self.assertTrue(default_storage.exists(job.input_file))
        name = job.input_file
        with self.captureOnCommitCallbacks(execute=True):
            job.delete()
        self.assertFalse(default_storage.exists(name))


class ExecuteJobTests(TestCase):
    def setUp(self):
        CALLS.clear()
        self.user = make_user('runner')

    def test_a_job_that_succeeds_records_its_summary_and_file(self):
        job = start_job(self.user, 'test_ok')

        self.assertEqual(run_pending_jobs(), ['jobs.run.test_ok'])

        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundJob.Status.SUCCEEDED)
        self.assertEqual(job.result, {'count': 3})
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.finished_at)
        self.assertEqual(job.result_filename, 'hello.txt')
        self.assertTrue(job.has_downloadable_result)
        self.assertIsNotNone(job.expires_at)

    def test_a_refusal_the_user_can_act_on_fails_the_job_with_its_message(self):
        job = start_job(self.user, 'test_refuse')

        run_pending_jobs()

        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundJob.Status.FAILED)
        self.assertEqual(job.error, 'That file is damaged.')
        self.assertEqual(job.error_code, 'invalid_backup')
        self.assertEqual(job.result, {'detail_key': 'x'})

    def test_an_unexpected_error_is_hidden_from_the_user_and_raised_for_the_queue(self):
        job = start_job(self.user, 'test_boom')

        with self.assertRaises(_Boom), self.assertLogs('jobs.registry', 'ERROR'):
            run_pending_jobs()

        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundJob.Status.FAILED)
        self.assertEqual(job.error_code, 'server_error')
        self.assertNotIn('secret', job.error)

    def test_a_job_cancelled_before_it_starts_does_not_run(self):
        job = start_job(self.user, 'test_ok')
        BackgroundJob.objects.filter(pk=job.pk).update(status=BackgroundJob.Status.CANCELLED)

        run_pending_jobs()

        self.assertEqual(CALLS, [])

    def test_a_deleted_job_does_not_run(self):
        job = start_job(self.user, 'test_ok')
        job.delete()

        run_pending_jobs()

        self.assertEqual(CALLS, [])

    def test_a_job_that_needs_its_upload_fails_when_the_upload_is_gone(self):
        job = start_job(self.user, 'test_needs_file')

        run_pending_jobs()

        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundJob.Status.FAILED)
        self.assertEqual(job.error_code, 'input_missing')

    def test_running_twice_after_a_stall_starts_over(self):
        job = start_job(self.user, 'test_ok')
        execute_job(job.id)
        execute_job(job.id)

        self.assertEqual(len(CALLS), 2)
        job.refresh_from_db()
        self.assertEqual(job.status, BackgroundJob.Status.SUCCEEDED)
