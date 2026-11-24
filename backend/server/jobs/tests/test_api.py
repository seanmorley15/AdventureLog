"""The jobs API: who sees a job, downloading its file, cancelling and removing."""

from datetime import timedelta

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.test import APITestCase

from core.testing import make_user
from jobs.models import BackgroundJob
from jobs.registry import start_job
from jobs.testing import queued_jobs, run_pending_jobs
from jobs.tests import test_registry  # noqa: F401  (registers the test_* job kinds)


class JobsApiTests(APITestCase):
    def setUp(self):
        self.owner = make_user('job-owner')
        self.other = make_user('job-other')
        self.client.force_authenticate(self.owner)

    def finished_job(self):
        job = start_job(self.owner, 'test_ok')
        run_pending_jobs()
        job.refresh_from_db()
        return job

    def test_the_list_holds_only_my_jobs_newest_first(self):
        first = start_job(self.owner, 'test_ok')
        second = start_job(self.owner, 'test_ok')
        start_job(self.other, 'test_ok')

        response = self.client.get('/api/jobs/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.json()], [str(second.id), str(first.id)])

    def test_a_job_shows_its_status_result_and_download_url(self):
        job = self.finished_job()

        body = self.client.get(f'/api/jobs/{job.id}/').json()

        self.assertEqual(body['status'], 'succeeded')
        self.assertEqual(body['result'], {'count': 3})
        self.assertEqual(body['filename'], 'hello.txt')
        self.assertEqual(body['download_url'], f'/api/jobs/{job.id}/download/')
        self.assertNotIn('params', body)
        self.assertNotIn('input_file', body)

    def test_a_queued_job_has_no_download_url(self):
        job = start_job(self.owner, 'test_ok')

        body = self.client.get(f'/api/jobs/{job.id}/').json()

        self.assertEqual(body['status'], 'queued')
        self.assertIsNone(body['download_url'])

    def test_another_users_job_is_not_found(self):
        job = self.finished_job()
        self.client.force_authenticate(self.other)

        self.assertEqual(self.client.get(f'/api/jobs/{job.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/jobs/{job.id}/download/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/jobs/{job.id}/').status_code, 404)

    def test_signing_in_is_required(self):
        self.client.force_authenticate(None)

        self.assertIn(self.client.get('/api/jobs/').status_code, (401, 403))

    def test_the_owner_downloads_the_file(self):
        job = self.finished_job()

        response = self.client.get(f'/api/jobs/{job.id}/download/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'hello')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('hello.txt', response['Content-Disposition'])
        self.assertEqual(response['Content-Type'], 'text/plain')

    def test_an_expired_file_is_gone(self):
        job = self.finished_job()
        BackgroundJob.objects.filter(pk=job.pk).update(expires_at=timezone.now() - timedelta(minutes=1))

        response = self.client.get(f'/api/jobs/{job.id}/download/')

        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json()['code'], 'job_expired')
        self.assertIsNone(self.client.get(f'/api/jobs/{job.id}/').json()['download_url'])

    def test_a_job_without_a_file_has_nothing_to_download(self):
        job = start_job(self.owner, 'test_ok')

        self.assertEqual(self.client.get(f'/api/jobs/{job.id}/download/').status_code, 404)

    def test_the_files_are_not_served_by_the_media_route(self):
        job = self.finished_job()

        response = self.client.get(f'/media/{job.result_file}')

        self.assertIn(response.status_code, (403, 404))

    def test_removing_a_queued_job_cancels_it(self):
        job = start_job(self.owner, 'test_ok')

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(f'/api/jobs/{job.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(BackgroundJob.objects.filter(pk=job.pk).exists())
        self.assertEqual(queued_jobs().count(), 0)

    def test_removing_a_finished_job_deletes_its_file(self):
        job = self.finished_job()
        name = job.result_file
        self.assertTrue(default_storage.exists(name))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(f'/api/jobs/{job.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(default_storage.exists(name))

    def test_a_running_job_cannot_be_removed(self):
        job = start_job(self.owner, 'test_ok')
        BackgroundJob.objects.filter(pk=job.pk).update(status=BackgroundJob.Status.RUNNING)

        response = self.client.delete(f'/api/jobs/{job.id}/')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'job_running')
        self.assertTrue(BackgroundJob.objects.filter(pk=job.pk).exists())

    def test_deleting_the_account_deletes_the_files(self):
        job = self.finished_job()
        name = job.result_file

        with self.captureOnCommitCallbacks(execute=True):
            self.owner.delete()

        self.assertFalse(BackgroundJob.objects.filter(pk=job.pk).exists())
        self.assertFalse(default_storage.exists(name))
