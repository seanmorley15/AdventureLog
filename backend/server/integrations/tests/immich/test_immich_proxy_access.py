from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionGuestLink, CollectionMember, ContentImage, Location, Lodging
from integrations.models import ImmichIntegration
from core.testing import make_user


class ImmichProxyAccessTests(APITestCase):
    def setUp(self):
        self.owner = make_user('proxy-owner')
        self.editor = make_user('proxy-editor')
        self.viewer = make_user('proxy-viewer')
        self.stranger = make_user('proxy-stranger')
        self.integration = ImmichIntegration.objects.create(
            user=self.owner, server_url='http://immich.example.com/api', api_key='k'
        )

        self.trip = Collection.objects.create(user=self.owner, name='Private trip')
        self.trip.shared_with.add(self.editor, self.viewer)
        CollectionMember.objects.filter(collection=self.trip, user=self.viewer).update(role='viewer')
        self.guest_link = CollectionGuestLink.objects.create(collection=self.trip, role='viewer', label='Family')
        self.story = Collection.objects.create(user=self.owner, name='Public story', visibility='public')

        self.public_place = Location.objects.create(user=self.owner, name='Public place', is_public=True)
        self.trip_place = Location.objects.create(user=self.owner, name='Trip place')
        self.trip_place.collections.add(self.trip)
        self.story_place = Location.objects.create(user=self.owner, name='Story place')
        self.story_place.collections.add(self.story)
        self.loose_place = Location.objects.create(user=self.owner, name='Loose place')
        self.trip_lodging = Lodging.objects.create(user=self.owner, collection=self.trip, name='Hut')
        self.public_trip_lodging = Lodging.objects.create(
            user=self.owner, collection=self.trip, name='Flagged hut', is_public=True
        )

        self.assets = {}
        for key, obj in {
            'public': self.public_place,
            'trip': self.trip_place,
            'story': self.story_place,
            'loose': self.loose_place,
            'lodging': self.trip_lodging,
            'flagged-lodging': self.public_trip_lodging,
        }.items():
            ContentImage.objects.create(
                user=self.owner,
                content_type=ContentType.objects.get_for_model(type(obj)),
                object_id=obj.id,
                immich_id=f'asset-{key}',
                source=ContentImage.Source.IMMICH,
            )
            self.assets[key] = f'asset-{key}'

        patcher = patch('integrations.views.immich.immich_get')
        self.fetch = patcher.start()
        self.addCleanup(patcher.stop)
        image = MagicMock(content=b'jpeg-bytes')
        image.headers = {'Content-Type': 'image/jpeg'}
        self.fetch.return_value = image

    def get(self, key, **extra):
        return self.client.get(f'/api/integrations/immich/{self.integration.id}/get/{self.assets[key]}/', **extra)

    def assertAllowed(self, key, user=None, **extra):
        self.client.force_authenticate(user=user)
        response = self.get(key, **extra)
        self.assertEqual(response.status_code, 200, f'{key} as {user}: {response.content[:200]}')
        return response

    def assertDenied(self, key, user=None, status=403, **extra):
        self.client.force_authenticate(user=user)
        response = self.get(key, **extra)
        self.assertEqual(response.status_code, status, f'{key} as {user}: {response.content[:200]}')

    def test_owner_can_read_everything_of_their_own(self):
        for key in self.assets:
            self.assertAllowed(key, self.owner)

    def test_public_place_is_readable_by_anyone_and_may_be_cached_publicly(self):
        response = self.assertAllowed('public', None)

        self.assertTrue(response['Cache-Control'].startswith('public'))

    def test_story_collection_photos_are_readable_by_anyone(self):
        self.assertAllowed('story', None)

    def test_collection_members_read_private_places_and_lodging_but_cache_privately(self):
        for member in (self.editor, self.viewer):
            self.assertAllowed('trip', member)
            self.assertAllowed('lodging', member)
        response = self.assertAllowed('trip', self.editor)
        self.assertTrue(response['Cache-Control'].startswith('private'))

    def test_a_guest_link_reads_the_collections_photos(self):
        response = self.assertAllowed('trip', None, HTTP_X_GUEST_TOKEN=self.guest_link.token)

        self.assertTrue(response['Cache-Control'].startswith('private'))
        self.assertAllowed('lodging', None, HTTP_X_GUEST_TOKEN=self.guest_link.token)

    def test_strangers_and_anonymous_visitors_cannot_read_private_photos(self):
        for key in ('trip', 'lodging', 'loose'):
            self.assertDenied(key, self.stranger)
            self.assertDenied(key, None)

    def test_a_lodging_in_a_collection_ignores_its_own_public_flag(self):
        self.assertDenied('flagged-lodging', self.stranger)
        self.assertDenied('flagged-lodging', None)
        self.assertAllowed('flagged-lodging', self.editor)

    def test_a_revoked_guest_link_stops_working(self):
        from django.utils import timezone

        self.guest_link.revoked_at = timezone.now()
        self.guest_link.save()

        self.assertDenied('trip', None, HTTP_X_GUEST_TOKEN=self.guest_link.token)

    def test_a_guest_link_does_not_open_other_collections(self):
        self.assertDenied('loose', None, HTTP_X_GUEST_TOKEN=self.guest_link.token)

    def test_an_asset_with_no_photo_record_is_only_for_the_integration_owner(self):
        self.assets['orphan'] = 'asset-orphan'

        self.assertAllowed('orphan', self.owner)
        self.assertDenied('orphan', self.stranger, status=404)
        self.assertDenied('orphan', None, status=404)
