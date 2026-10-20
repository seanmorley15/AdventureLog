"""Base classes for tests that need a shared trip with an owner, an editor, a viewer and a stranger."""

from datetime import date

from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionMember, Location
from adventures.services.day_plan import convert_collection
from core.testing import make_user as core_make_user


def make_user(name, **extra):
    """A user other people can find and share with."""
    return core_make_user(name, password='pw-12345678', public_profile=True, **extra)


class AudienceTestBase(APITestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.editor = make_user('editor')
        self.viewer = make_user('viewer')
        self.stranger = make_user('stranger')
        self.trip = Collection.objects.create(
            user=self.owner, name='Lofoten', type='trip',
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 3),
        )
        convert_collection(self.trip)
        self.trip.shared_with.add(self.editor, self.viewer)
        CollectionMember.objects.filter(collection=self.trip, user=self.viewer).update(role='viewer')

        self.hut = Location.objects.create(user=self.owner, name='Hut', is_public=False, location='Reine 1')
        self.hut.collections.add(self.trip)
        from adventures.services.day_plan import place_object, get_day_by_index
        from django.contrib.contenttypes.models import ContentType

        self.stop, _ = place_object(
            self.trip, ContentType.objects.get_for_model(Location), self.hut.id, day=get_day_by_index(self.trip, 1)
        )

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def as_anonymous(self):
        self.client.force_authenticate(user=None)

    def move_stop(self, day_index=2, **headers):
        return self.client.patch(
            f'/api/itineraries/{self.stop.id}/', {'day_index': day_index}, format='json', **headers
        )

    def publish(self, visibility='public', **groups):
        self.trip.visibility = visibility
        self.trip.story_groups = groups
        self.trip.save()
