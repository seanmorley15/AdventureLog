import uuid

from rest_framework.test import APITestCase

from adventures.models import Location
from users.models import CustomUser


class ContentObjectResolutionTests(APITestCase):
    """The validation images and attachments share before attaching a file to a record."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='attach-user', email='attach-user@example.com', password='testpassword123'
        )
        self.stranger = CustomUser.objects.create_user(
            username='attach-stranger', email='attach-stranger@example.com', password='testpassword123'
        )
        self.private = Location.objects.create(user=self.stranger, name='Private', is_public=False)
        self.client.force_authenticate(user=self.user)

    def _post(self, url, **data):
        return self.client.post(url, data, format='json')

    # ---- images: allow 8 types, and the id must be a UUID

    def test_images_reject_unknown_content_type_and_list_the_allowed_ones(self):
        response = self._post('/api/images/', content_type='bogus', object_id=str(self.private.id))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()['fields']), {'content_type'})

    def test_images_reject_undefined_object_id(self):
        response = self._post('/api/images/', content_type='location', object_id='undefined')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()['fields']), {'object_id'})

    def test_images_reject_malformed_object_id(self):
        response = self._post('/api/images/', content_type='location', object_id='not-a-uuid')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()['fields']), {'object_id'})

    def test_images_report_missing_records(self):
        response = self._post('/api/images/', content_type='location', object_id=str(uuid.uuid4()))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'location not found.')

    def test_images_refuse_someone_elses_private_record(self):
        response = self._post('/api/images/', content_type='location', object_id=str(self.private.id))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'permission_denied')

    def test_import_from_urls_uses_the_same_validation(self):
        response = self._post(
            '/api/images/import-from-urls/',
            content_type='bogus', object_id=str(self.private.id), urls=['https://example.com/a.jpg'],
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()['fields']), {'content_type'})

    # ---- attachments: allow 5 types

    def test_attachments_reject_types_that_only_images_accept(self):
        response = self._post('/api/attachments/', content_type='trail', object_id=str(uuid.uuid4()))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()['fields']), {'content_type'})

    def test_attachments_report_missing_records(self):
        response = self._post('/api/attachments/', content_type='note', object_id=str(uuid.uuid4()))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'note not found.')

    def test_attachments_refuse_someone_elses_private_record(self):
        response = self._post('/api/attachments/', content_type='location', object_id=str(self.private.id))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['code'], 'permission_denied')

    def test_attachments_still_require_both_fields(self):
        response = self._post('/api/attachments/', content_type='location')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()['fields']), {'object_id'})
