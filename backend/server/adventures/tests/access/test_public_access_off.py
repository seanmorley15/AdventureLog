"""A server with ALLOW_PUBLIC_ACCESS off is for signed-in users only (#1124)."""

import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import override_settings

from adventures.models import CollectionGuestLink, ContentImage, Location, Lodging
from adventures.tests.base import AudienceTestBase
from adventures.tests.factories import PNG


@override_settings(ALLOW_PUBLIC_ACCESS=False)
class PublicAccessOffTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.place = Location.objects.create(user=self.owner, name='Viewpoint', is_public=True)
        self.stay = Lodging.objects.create(user=self.owner, name='Cabin', type='cabin', is_public=True)

    def get(self, url, user=None, **params):
        self.client.force_authenticate(user=user)
        return self.client.get(url, params)

    def test_public_and_unlisted_stories_are_for_signed_in_readers_only(self):
        url = f'/api/collections/{self.trip.id}/'
        self.publish('public')
        self.assertEqual(self.get(url).status_code, 404)
        self.assertEqual(self.get(url, self.stranger).status_code, 200)

        self.publish('unlisted')
        secret = self.trip.share_secret
        self.assertEqual(self.get(url, s=secret).status_code, 404)
        self.assertEqual(self.get(url, self.stranger, s=secret).status_code, 200)

    def test_guest_links_stop_working_and_none_can_be_made(self):
        link = CollectionGuestLink.objects.create(collection=self.trip, role='viewer')
        self.client.force_authenticate(user=None)
        response = self.client.get(f'/api/collections/{self.trip.id}/', HTTP_X_GUEST_TOKEN=link.token)
        self.assertEqual(response.status_code, 404)

        self.as_user(self.owner)
        refused = self.client.post(f'/api/collections/{self.trip.id}/guest-links/', {'role': 'viewer'}, format='json')
        self.assertEqual(refused.status_code, 400, refused.content)
        self.assertEqual(CollectionGuestLink.objects.filter(collection=self.trip).count(), 1)

    def test_public_places_and_records_are_shown_to_signed_in_users_only(self):
        for url in (f'/api/locations/{self.place.id}/', f'/api/lodgings/{self.stay.id}/'):
            self.assertIn(self.get(url).status_code, (401, 403, 404), url)
            self.assertEqual(self.get(url, self.stranger).status_code, 200, url)
        self.assertIn(self.get(f'/api/locations/{self.place.id}/share-image/square/').status_code, (401, 403, 404))

    def test_photos_of_public_places_are_shown_to_signed_in_users_only(self):
        photo = ContentImage.objects.create(
            user=self.owner, content_object=self.place, image=ContentFile(PNG, name='view.png')
        )
        path = f'/media/{photo.image.name}'

        self.assertIn(self.client.get(path).status_code, (403, 404))
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(path).status_code, 200)

    def test_the_server_says_public_access_is_off(self):
        self.assertFalse(self.get('/api/server-info/').json()['allow_public_access'])


@override_settings(ALLOW_PUBLIC_ACCESS=True)
class PublicAccessOnTests(AudienceTestBase):
    """The default: what is public stays open to everyone."""

    def test_public_places_stories_and_guest_links_work_for_visitors(self):
        place = Location.objects.create(user=self.owner, name='Viewpoint', is_public=True)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(f'/api/locations/{place.id}/').status_code, 200)

        self.publish('public')
        self.assertEqual(self.client.get(f'/api/collections/{self.trip.id}/').status_code, 200)

        self.publish('private')
        link = CollectionGuestLink.objects.create(collection=self.trip, role='viewer')
        response = self.client.get(f'/api/collections/{self.trip.id}/', HTTP_X_GUEST_TOKEN=link.token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.get('/api/server-info/').json()['allow_public_access'])
