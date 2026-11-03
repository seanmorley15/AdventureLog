from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase

from adventures.models import Collection, ContentImage, Location
from integrations.models import ImmichIntegration
from users.models import CustomUser


class ContentImageSourceImmutableTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='image-owner', email='image-owner@example.com', password='testpassword123'
        )
        self.editor = CustomUser.objects.create_user(
            username='image-editor', email='image-editor@example.com', password='testpassword123'
        )
        ImmichIntegration.objects.create(user=self.owner, server_url='http://immich.example.com/api', api_key='k')
        self.collection = Collection.objects.create(user=self.owner, name='Shared Trip')
        self.collection.shared_with.add(self.editor)
        self.location = Location.objects.create(user=self.owner, name='Shared Place')
        self.location.collections.add(self.collection)
        self.image = ContentImage.objects.create(
            user=self.owner,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.location.id,
            immich_id='owner-asset-1',
            source=ContentImage.Source.IMMICH,
        )
        self.detail = f'/api/images/{self.image.id}/'

    def test_editor_cannot_repoint_image_at_another_immich_asset(self):
        self.client.force_authenticate(user=self.editor)

        response = self.client.patch(
            self.detail,
            {'immich_id': 'owners-private-asset', 'source': 'upload', 'source_url': 'http://example.com/x.png'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.image.refresh_from_db()
        self.assertEqual(self.image.immich_id, 'owner-asset-1')
        self.assertEqual(self.image.source, ContentImage.Source.IMMICH)
        self.assertIsNone(self.image.source_url)

    def test_put_cannot_swap_immich_id_either(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.put(self.detail, {'immich_id': 'something-else', 'is_primary': False}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.image.refresh_from_db()
        self.assertEqual(self.image.immich_id, 'owner-asset-1')
