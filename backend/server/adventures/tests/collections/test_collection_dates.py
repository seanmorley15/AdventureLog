import datetime

from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionItineraryItem, Note
from users.models import CustomUser


class CollectionDateChangeTests(APITestCase):
    """Changing a collection's dates keeps its Trip Context items (#1328)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='planner', email='planner@example.com', password='testpassword'
        )
        self.client.force_authenticate(self.user)

    def _collection(self, type):
        return Collection.objects.create(
            user=self.user,
            name='Lisbon',
            type=type,
            start_date=datetime.date(2026, 11, 2),
            end_date=datetime.date(2026, 11, 5),
        )

    def _item(self, collection, name, **placement):
        note = Note.objects.create(user=self.user, name=name, collection=collection)
        return CollectionItineraryItem.objects.create(
            collection=collection,
            content_type=ContentType.objects.get_for_model(Note),
            object_id=note.id,
            order=CollectionItineraryItem.objects.filter(collection=collection).count(),
            **placement,
        )

    def _shorten(self, collection, **extra):
        response = self.client.patch(
            f'/api/collections/{collection.id}/',
            {'start_date': '2026-11-02', 'end_date': '2026-11-04', **extra},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

    def test_a_folder_planned_by_date_keeps_trip_context_when_its_dates_change(self):
        collection = self._collection(Collection.Type.FOLDER)
        packing = self._item(collection, 'Packing list', is_global=True)
        inside = self._item(collection, 'Tram 28', date=datetime.date(2026, 11, 3))
        outside = self._item(collection, 'Sintra', date=datetime.date(2026, 11, 5))

        self._shorten(collection, type='folder')

        remaining = set(CollectionItineraryItem.objects.filter(collection=collection).values_list('id', flat=True))
        self.assertIn(packing.id, remaining)
        self.assertIn(inside.id, remaining)
        self.assertNotIn(outside.id, remaining)

    def test_a_trip_planned_by_date_keeps_trip_context_when_its_dates_change(self):
        collection = self._collection(Collection.Type.TRIP)
        packing = self._item(collection, 'Packing list', is_global=True)

        self._shorten(collection)

        packing.refresh_from_db()
        self.assertTrue(packing.is_global)
