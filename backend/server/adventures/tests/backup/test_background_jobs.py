"""Exports and imports that run in the background: start, run the queued job, poll, download."""

import io
import json
import shutil
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import Collection, Location
from adventures.tests.factories import build_rich_account
from jobs.models import BackgroundJob
from jobs.testing import queued_jobs, run_pending_jobs
from users.models import CustomUser

ASYNC = {'HTTP_PREFER': 'respond-async'}


class BackgroundJobsTestBase(APITestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root, ADVENTURELOG_RELEASE_VERSION='test')
        override.enable()
        self.addCleanup(override.disable)

        self.owner = CustomUser.objects.create_user(username='bg-owner', email='bg-owner@example.com', password='testpassword123')
        self.friend = CustomUser.objects.create_user(
            username='bg-friend', email='bg-friend@example.com', password='testpassword123', public_profile=True
        )
        self.importer = CustomUser.objects.create_user(
            username='bg-importer', email='bg-importer@example.com', password='testpassword123'
        )
        self.objects = build_rich_account(self.owner, self.friend)
        self.trip = self.objects['trip']

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def start(self, method, url, user, **kwargs):
        """Call an endpoint that starts a job; returns the 202 body."""
        self.as_user(user)
        response = getattr(self.client, method)(url, **kwargs)
        self.assertEqual(response.status_code, 202, response.content)
        body = response.json()
        self.assertEqual(response['Location'], f'/api/jobs/{body["id"]}/')
        self.assertEqual(body['status'], 'queued')
        return body

    def finish(self, job_id, user, expect='succeeded'):
        """Run the queue and return the job as the user sees it."""
        run_pending_jobs()
        self.as_user(user)
        body = self.client.get(f'/api/jobs/{job_id}/').json()
        self.assertEqual(body['status'], expect, body)
        return body

    def download(self, body, user):
        self.as_user(user)
        response = self.client.get(body['download_url'])
        self.assertEqual(response.status_code, 200)
        return b''.join(response.streaming_content)


class BackgroundExportTests(BackgroundJobsTestBase):
    def test_an_account_backup_is_made_in_the_background(self):
        job = self.start('post', '/api/backup/export/', self.owner)

        done = self.finish(job['id'], self.owner)

        self.assertTrue(done['filename'].startswith('adventurelog_backup_bg-owner_'))
        with zipfile.ZipFile(io.BytesIO(self.download(done, self.owner))) as archive:
            data = json.loads(archive.read('data.json'))
        self.assertEqual(data['user_username'], 'bg-owner')
        self.assertEqual(len(data['collections']), Collection.objects.filter(user=self.owner).count())

    def test_a_collection_archive_is_made_in_the_background(self):
        job = self.start('post', f'/api/collections/{self.trip.id}/archive/', self.owner)

        done = self.finish(job['id'], self.owner)

        with zipfile.ZipFile(io.BytesIO(self.download(done, self.owner))) as archive:
            self.assertEqual(json.loads(archive.read('data.json'))['archive_kind'], 'collection')

    def test_only_the_owner_can_start_a_collection_archive(self):
        self.as_user(self.friend)

        response = self.client.post(f'/api/collections/{self.trip.id}/archive/')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(BackgroundJob.objects.count(), 0)

    def test_a_pdf_is_made_in_the_background(self):
        job = self.start('post', f'/api/collections/{self.trip.id}/pdf/', self.owner)

        done = self.finish(job['id'], self.owner)

        self.assertTrue(self.download(done, self.owner).startswith(b'%PDF'))
        self.assertEqual(BackgroundJob.objects.get(pk=job['id']).params['story'], False)

    def test_a_pdf_needs_a_signed_in_user_and_a_readable_collection(self):
        self.client.force_authenticate(None)
        anonymous = self.client.post(f'/api/collections/{self.trip.id}/pdf/')
        self.as_user(self.importer)
        stranger = self.client.post(f'/api/collections/{self.trip.id}/pdf/')

        self.assertIn(anonymous.status_code, (401, 403, 404))
        self.assertEqual(stranger.status_code, 404)
        self.assertEqual(BackgroundJob.objects.count(), 0)

    def test_the_file_is_private_to_the_user_who_asked(self):
        job = self.start('post', '/api/backup/export/', self.owner)
        done = self.finish(job['id'], self.owner)

        self.as_user(self.importer)

        self.assertEqual(self.client.get(done['download_url']).status_code, 404)

    def test_the_direct_downloads_still_work(self):
        self.as_user(self.owner)

        self.assertEqual(self.client.get('/api/backup/export/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/collections/{self.trip.id}/archive/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/collections/{self.trip.id}/pdf/').status_code, 200)
        self.assertEqual(BackgroundJob.objects.count(), 0)


class BackgroundImportTests(BackgroundJobsTestBase):
    def backup_bytes(self):
        job = self.start('post', '/api/backup/export/', self.owner)
        return self.download(self.finish(job['id'], self.owner), self.owner)

    def upload(self, url, content, user, **fields):
        self.as_user(user)
        file = SimpleUploadedFile('file.zip', content, content_type='application/zip')
        return self.client.post(url, {'file': file, **fields}, format='multipart', **ASYNC)

    def test_a_backup_is_restored_in_the_background(self):
        content = self.backup_bytes()
        self.assertEqual(Location.objects.filter(user=self.importer).count(), 0)

        response = self.upload('/api/backup/import/', content, self.importer, confirm='yes')

        self.assertEqual(response.status_code, 202, response.content)
        body = response.json()
        # Nothing has changed yet: the worker restores it.
        self.assertEqual(Location.objects.filter(user=self.importer).count(), 0)
        done = self.finish(body['id'], self.importer)
        self.assertGreater(done['result']['summary']['locations'], 0)
        self.assertGreater(Location.objects.filter(user=self.importer).count(), 0)
        # The staged upload is deleted once it has been used.
        self.assertEqual(BackgroundJob.objects.get(pk=body['id']).input_file, '')

    def test_the_file_is_checked_before_a_job_is_queued(self):
        self.as_user(self.importer)
        not_a_zip = SimpleUploadedFile('file.zip', b'definitely not a zip', content_type='application/zip')

        response = self.client.post('/api/backup/import/', {'file': not_a_zip, 'confirm': 'yes'}, format='multipart', **ASYNC)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'invalid_backup')
        self.assertEqual(BackgroundJob.objects.count(), 0)

    def test_confirmation_is_still_required(self):
        response = self.upload('/api/backup/import/', self.backup_bytes(), self.importer)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(BackgroundJob.objects.exclude(kind='account_export').count(), 0)

    def test_a_zip_that_is_not_a_backup_fails_the_job_and_deletes_nothing(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('readme.txt', 'hello')
        mine = Location.objects.filter(user=self.owner).count()
        self.assertGreater(mine, 0)

        response = self.upload('/api/backup/import/', buffer.getvalue(), self.owner, confirm='yes')
        done = self.finish(response.json()['id'], self.owner, expect='failed')

        self.assertEqual(done['error_code'], 'invalid_backup')
        self.assertIn('data.json', done['error'])
        self.assertEqual(Location.objects.filter(user=self.owner).count(), mine)

    def test_a_collection_is_imported_in_the_background(self):
        job = self.start('post', f'/api/collections/{self.trip.id}/archive/', self.owner)
        content = self.download(self.finish(job['id'], self.owner), self.owner)

        response = self.upload('/api/collections/import/', content, self.importer, existing_locations='create')
        self.assertEqual(response.status_code, 202, response.content)
        done = self.finish(response.json()['id'], self.importer)

        imported = Collection.objects.get(pk=done['result']['collection_id'])
        self.assertEqual(imported.user, self.importer)
        self.assertGreater(done['result']['summary']['locations'], 0)

    def test_the_direct_imports_still_work_without_the_header(self):
        content = self.backup_bytes()
        self.as_user(self.importer)
        file = SimpleUploadedFile('file.zip', content, content_type='application/zip')

        response = self.client.post('/api/backup/import/', {'file': file, 'confirm': 'yes'}, format='multipart')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(queued_jobs().count(), 0)


class BackgroundImageImportTests(BackgroundJobsTestBase):
    def setUp(self):
        super().setUp()
        self.place = Location.objects.create(user=self.owner, name='Image target')
        self.payload = {
            'content_type': 'location', 'object_id': str(self.place.id), 'urls': ['https://example.com/a.jpg'],
        }

    def post(self, user):
        self.as_user(user)
        return self.client.post('/api/images/import-from-urls/', self.payload, format='json', **ASYNC)

    def test_images_are_downloaded_in_the_background(self):
        image = MagicMock(pk='11111111-1111-1111-1111-111111111111')
        summary = {
            'created_images': [image], 'results': [{'url': 'https://example.com/a.jpg', 'status': 'created'}],
            'created_count': 1, 'requested_count': 1,
        }
        response = self.post(self.owner)
        self.assertEqual(response.status_code, 202, response.content)

        with patch('adventures.services.images.fetch.import_remote_images_for_object', return_value=summary) as fetch:
            done = self.finish(response.json()['id'], self.owner)

        self.assertEqual(done['result']['created_ids'], [str(image.pk)])
        self.assertEqual(done['result']['created_count'], 1)
        self.assertEqual(fetch.call_args.args[0], self.place)
        self.assertEqual(fetch.call_args.kwargs['owner'], self.owner)

    def test_a_job_where_no_image_could_be_imported_fails_with_the_results(self):
        results = [{'url': 'https://example.com/a.jpg', 'status': 'failed', 'error': 'nope'}]
        summary = {'created_images': [], 'results': results, 'created_count': 0, 'requested_count': 1}
        response = self.post(self.owner)

        with patch('adventures.services.images.fetch.import_remote_images_for_object', return_value=summary):
            done = self.finish(response.json()['id'], self.owner, expect='failed')

        self.assertEqual(done['error_code'], 'import_failed')
        self.assertEqual(done['result'], {'results': results})

    def test_someone_who_cannot_change_the_record_cannot_queue_an_import(self):
        response = self.post(self.importer)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(BackgroundJob.objects.count(), 0)
