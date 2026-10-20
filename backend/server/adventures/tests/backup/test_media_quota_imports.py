import io
import json
import shutil
import tempfile
import zipfile

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import Collection, ContentAttachment, Location
from adventures.utils.collection_type import BACKUP_SCHEMA
from users.models import CustomUser


class MediaQuotaTests(APITestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root, MEDIA_STORAGE_LIMIT_BYTES=1000)
        override.enable()
        self.addCleanup(override.disable)

        self.user = CustomUser.objects.create_user(
            username='quota-user', email='quota-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

    def _zip(self, members):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return SimpleUploadedFile('upload.zip', buffer.getvalue(), content_type='application/zip')

    def test_backup_import_over_the_limit_is_refused_before_anything_is_wiped(self):
        Collection.objects.create(user=self.user, name='Keep me')
        backup = {'backup_schema': BACKUP_SCHEMA, 'collections': [], 'locations': []}
        upload = self._zip({'data.json': json.dumps(backup), 'images/huge.webp': b'x' * 5000})

        response = self.client.post('/api/backup/import/', {'file': upload, 'confirm': 'yes'}, format='multipart')

        self.assertEqual(response.status_code, 413, response.content)
        self.assertEqual(response.json()['error'], 'Media storage limit exceeded')
        self.assertTrue(Collection.objects.filter(user=self.user, name='Keep me').exists())

    def test_backup_import_within_the_limit_still_works(self):
        backup = {'backup_schema': BACKUP_SCHEMA, 'collections': [], 'locations': []}
        upload = self._zip({'data.json': json.dumps(backup), 'images/small.webp': b'x' * 100})

        response = self.client.post('/api/backup/import/', {'file': upload, 'confirm': 'yes'}, format='multipart')

        self.assertEqual(response.status_code, 200, response.content)

    def test_collection_import_over_the_limit_is_refused(self):
        upload = self._zip({'metadata.json': json.dumps({'collection': {'name': 'Big'}}), 'images/huge.webp': b'x' * 5000})

        response = self.client.post('/api/collections/import/', {'file': upload}, format='multipart')

        self.assertEqual(response.status_code, 413, response.content)
        self.assertFalse(Collection.objects.filter(user=self.user, name='Big').exists())

    def test_replacing_an_attachment_with_a_file_over_the_limit_is_refused(self):
        location = Location.objects.create(user=self.user, name='Place')
        attachment = ContentAttachment(
            user=self.user,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=location.id,
            name='notes',
        )
        attachment.file.save('notes.txt', ContentFile(b'small'), save=True)

        response = self.client.patch(
            f'/api/attachments/{attachment.id}/',
            {'file': SimpleUploadedFile('big.txt', b'x' * 5000)},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400, response.content)
        attachment.refresh_from_db()
        self.assertTrue(attachment.file.name.endswith('.txt'))
        self.assertEqual(attachment.file.size, 5)

    def test_renaming_an_attachment_without_a_new_file_is_not_limited(self):
        location = Location.objects.create(user=self.user, name='Place')
        attachment = ContentAttachment(
            user=self.user,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=location.id,
            name='notes',
        )
        attachment.file.save('notes.txt', ContentFile(b'small'), save=True)

        response = self.client.patch(f'/api/attachments/{attachment.id}/', {'name': 'renamed'}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
