from unittest.mock import patch

from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionGuestLink, CollectionMember, Location
from core.testing import make_user


class SunriseSunsetLocationAccessTests(APITestCase):
    """The public sunrise endpoint reveals where a place is, so it follows who may read the place."""

    URL = '/api/sunrise-sunset/lookup/'

    def setUp(self):
        from core.geo import make_point

        self.owner = make_user('sun-owner')
        self.editor = make_user('sun-editor')
        self.viewer = make_user('sun-viewer')
        self.stranger = make_user('sun-stranger')
        self.trip = Collection.objects.create(user=self.owner, name='Trip')
        self.trip.shared_with.add(self.editor, self.viewer)
        CollectionMember.objects.filter(collection=self.trip, user=self.viewer).update(role='viewer')
        self.guest_link = CollectionGuestLink.objects.create(collection=self.trip, role='viewer')
        self.place = Location.objects.create(user=self.owner, name='Hut', coordinates=make_point(13.0, 67.9))
        self.place.collections.add(self.trip)
        self.public_place = Location.objects.create(
            user=self.owner, name='Lookout', coordinates=make_point(13.1, 67.8), is_public=True
        )
        self.loose_place = Location.objects.create(user=self.owner, name='Home', coordinates=make_point(10.7, 59.9))
        patcher = patch(
            'adventures.views.sunrise_sunset.get_sunrise_sunset_for_date',
            return_value={'sunrise': '03:00', 'sunset': '23:00'},
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def lookup(self, location, user=None, **extra):
        self.client.force_authenticate(user=user)
        return self.client.get(self.URL, {'location_id': str(location.id), 'date': '2026-06-21'}, **extra)

    def test_public_place_is_open_to_anyone(self):
        self.assertEqual(self.lookup(self.public_place).status_code, 200)

    def test_owner_and_collection_members_can_look_up_a_private_place(self):
        for user in (self.owner, self.editor, self.viewer):
            self.assertEqual(self.lookup(self.place, user).status_code, 200, user)

    def test_a_guest_link_can_look_up_places_in_its_collection_only(self):
        header = {'HTTP_X_GUEST_TOKEN': self.guest_link.token}

        self.assertEqual(self.lookup(self.place, **header).status_code, 200)
        self.assertEqual(self.lookup(self.loose_place, **header).status_code, 403)

    def test_strangers_and_anonymous_visitors_are_refused(self):
        for user in (self.stranger, None):
            self.assertEqual(self.lookup(self.place, user).status_code, 403, user)
            self.assertEqual(self.lookup(self.loose_place, user).status_code, 403, user)


class LocationAdditionalInfoAccessTests(APITestCase):
    def setUp(self):
        self.owner = make_user('info-owner')
        self.viewer = make_user('info-viewer')
        self.stranger = make_user('info-stranger')
        self.trip = Collection.objects.create(user=self.owner, name='Trip')
        self.trip.shared_with.add(self.viewer)
        CollectionMember.objects.filter(collection=self.trip, user=self.viewer).update(role='viewer')
        self.place = Location.objects.create(user=self.owner, name='Hut')
        self.place.collections.add(self.trip)

    def test_members_read_additional_info_and_strangers_cannot(self):
        url = f'/api/locations/{self.place.id}/additional-info/'
        for user, expected in ((self.owner, 200), (self.viewer, 200), (self.stranger, 404)):
            self.client.force_authenticate(user=user)
            self.assertEqual(self.client.get(url).status_code, expected, user)

    def test_a_viewer_cannot_duplicate_a_place(self):
        self.client.force_authenticate(user=self.viewer)

        response = self.client.post(f'/api/locations/{self.place.id}/duplicate/', {}, format='json')

        self.assertIn(response.status_code, (403, 404))
        self.assertEqual(Location.objects.filter(name__startswith='Copy of').count(), 0)
