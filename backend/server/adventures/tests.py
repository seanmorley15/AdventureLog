from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APITestCase

from adventures.geocoding import extractIsoCode
from adventures.models import Collection, CollectionItineraryItem, Location, Note, Visit
from routing.exceptions import OSRMUnavailableError
from users.models import CustomUser
from worldtravel.models import City, Country, Region


class ItineraryAPITestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='itinerary-user',
            email='itinerary-user@example.com',
            password='testpassword123',
        )
        self.collection = Collection.objects.create(user=self.user, name='Test Trip')
        self.location = Location.objects.create(user=self.user, name='Test Location', is_public=True)
        self.client.force_authenticate(user=self.user)

    def test_create_global_itinerary_item_without_date(self):
        response = self.client.post(
            '/api/itineraries/',
            {
                'collection': str(self.collection.id),
                'content_type': 'location',
                'object_id': str(self.location.id),
                'is_global': True,
                'order': 0,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(CollectionItineraryItem.objects.count(), 1)

        item = CollectionItineraryItem.objects.get()
        self.assertTrue(item.is_global)
        self.assertIsNone(item.date)
        self.assertEqual(item.collection, self.collection)

        payload = response.json()
        self.assertTrue(payload['is_global'])
        self.assertIsNone(payload['date'])

    def test_create_dated_itinerary_item_without_date_is_rejected(self):
        response = self.client.post(
            '/api/itineraries/',
            {
                'collection': str(self.collection.id),
                'content_type': 'location',
                'object_id': str(self.location.id),
                'is_global': False,
                'order': 0,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['date'][0], 'Dated items must include a date. To create a trip-wide item, set is_global=true.')


class ItineraryOptimizeEndpointTests(APITestCase):
    """Endpoint-level tests for POST /api/itineraries/optimize/, with the
    OSRM call mocked (routing/tests.py covers the OSRM client and the
    optimize_order algorithm in isolation).
    """

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='optimize-user',
            email='optimize-user@example.com',
            password='testpassword123',
        )
        self.collection = Collection.objects.create(user=self.user, name='Italy Trip')
        self.client.force_authenticate(user=self.user)

        self.loc_a = Location.objects.create(user=self.user, name='A', latitude=41.9, longitude=12.5)
        self.loc_b = Location.objects.create(user=self.user, name='B', latitude=43.7, longitude=11.3)
        self.loc_c = Location.objects.create(user=self.user, name='C', latitude=45.4, longitude=9.2)

        self.visit_a = Visit.objects.create(location=self.loc_a)
        self.visit_b = Visit.objects.create(location=self.loc_b)
        self.visit_c = Visit.objects.create(location=self.loc_c)

        visit_ct = ContentType.objects.get_for_model(Visit)
        self.item_a = CollectionItineraryItem.objects.create(
            collection=self.collection, content_type=visit_ct, object_id=self.visit_a.id,
            date='2026-08-01', order=0,
        )
        self.item_b = CollectionItineraryItem.objects.create(
            collection=self.collection, content_type=visit_ct, object_id=self.visit_b.id,
            date='2026-08-01', order=1,
        )
        self.item_c = CollectionItineraryItem.objects.create(
            collection=self.collection, content_type=visit_ct, object_id=self.visit_c.id,
            date='2026-08-01', order=2,
        )

        # A Note on the same day: no coordinates, must be skipped and its
        # order slot (3) must never be reassigned to a Visit.
        note = Note.objects.create(user=self.user, name='Lembrete', date='2026-08-01')
        note_ct = ContentType.objects.get_for_model(Note)
        self.note_item = CollectionItineraryItem.objects.create(
            collection=self.collection, content_type=note_ct, object_id=note.id,
            date='2026-08-01', order=3,
        )

    def _optimize(self, **overrides):
        payload = {"collection_id": str(self.collection.id), "date": "2026-08-01"}
        payload.update(overrides)
        return self.client.post('/api/itineraries/optimize/', payload, format='json')

    @patch('adventures.views.itinerary_view.get_duration_matrix')
    def test_optimize_returns_cheaper_order_and_skips_note(self, mock_matrix):
        # Stops arrive as A, B, C (indices 0,1,2 in that order, matching
        # their .order values). A->B and B->C are both expensive; A->C is
        # cheap, so a good tour avoids ever going straight A->B->C.
        mock_matrix.return_value = [
            [0, 100, 10],
            [100, 0, 100],
            [10, 100, 0],
        ]

        response = self._optimize()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['optimized'])
        self.assertEqual(data['skipped_item_ids'], [str(self.note_item.id)])
        self.assertEqual(data['current_total_duration_seconds'], 200)  # A->B (100) + B->C (100)
        self.assertEqual(data['proposed_total_duration_seconds'], 110)  # best achievable path cost

        proposed_ids = {entry['id'] for entry in data['proposed_order']}
        self.assertEqual(
            proposed_ids, {str(self.item_a.id), str(self.item_b.id), str(self.item_c.id)}
        )
        # The Note's own order slot (3) must never be handed to a reordered stop.
        self.assertNotIn(3, [entry['order'] for entry in data['proposed_order']])
        # The three Visit order slots (0,1,2) must be exactly reused, just permuted.
        self.assertEqual(
            sorted(entry['order'] for entry in data['proposed_order']), [0, 1, 2]
        )

    @patch('adventures.views.itinerary_view.get_duration_matrix')
    def test_optimize_returns_503_when_osrm_unavailable(self, mock_matrix):
        mock_matrix.side_effect = OSRMUnavailableError("OSRM_URL não configurada")

        response = self._optimize()

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()['optimized'])

    def test_optimize_with_a_single_stop_reports_nothing_to_optimize(self):
        # Remove two of the three stops so only one remains — OSRM is never
        # even called in this case (asserted implicitly: no mock/patch here,
        # so a real call would fail loudly if the view tried to make one).
        self.item_b.delete()
        self.item_c.delete()

        response = self._optimize()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['optimized'])

    def test_optimize_denies_users_without_access_to_the_collection(self):
        intruder = CustomUser.objects.create_user(
            username='intruder', email='intruder@example.com', password='testpassword123',
        )
        self.client.force_authenticate(user=intruder)

        response = self._optimize()

        self.assertEqual(response.status_code, 403)

    @patch('adventures.views.itinerary_view.get_duration_matrix')
    def test_optimize_resolves_stops_added_via_the_location_quick_add_flow(self, mock_matrix):
        # Regression test (P2.5 audit, 2026-07-19): the itinerary UI's "+" ->
        # "Location" menu is the only way to add a stop from the day view,
        # and it creates the CollectionItineraryItem with content_type=Location
        # directly (a Visit is created alongside it for calendar display, but
        # it isn't what the itinerary item links to). Before this fix,
        # resolve_item_coordinates only recognized Visit/Lodging, so these
        # items were always skipped and "Otimizar rota" never had >=2
        # resolvable stops to work with.
        location_ct = ContentType.objects.get_for_model(Location)
        loc_d = Location.objects.create(user=self.user, name='D', latitude=41.89, longitude=12.49)
        loc_e = Location.objects.create(user=self.user, name='E', latitude=41.90, longitude=12.48)

        item_d = CollectionItineraryItem.objects.create(
            collection=self.collection, content_type=location_ct, object_id=loc_d.id,
            date='2026-08-02', order=0,
        )
        item_e = CollectionItineraryItem.objects.create(
            collection=self.collection, content_type=location_ct, object_id=loc_e.id,
            date='2026-08-02', order=1,
        )

        mock_matrix.return_value = [[0, 50], [50, 0]]

        response = self._optimize(date='2026-08-02')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['optimized'])
        self.assertEqual(data['skipped_item_ids'], [])
        proposed_ids = {entry['id'] for entry in data['proposed_order']}
        self.assertEqual(proposed_ids, {str(item_d.id), str(item_e.id)})


class ExtractIsoCodeLocalityMatchTests(TestCase):
    """Regression for issue #2: reverse geocode picked 'Arcinazzo Romano' for Rome centre."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geocode-user',
            email='geocode-user@example.com',
            password='testpassword123',
        )
        self.country = Country.objects.create(name='Italy', country_code='IT')
        self.region = Region.objects.create(id='IT-62', name='Lazio', country=self.country)
        # Decoy city whose name contains "Roma" as a substring but is a different place.
        City.objects.create(id='IT-arcinazzo', name='Arcinazzo Romano', region=self.region)
        self.rome = City.objects.create(id='IT-roma', name='Rome', region=self.region)

    def _geocode_data(self, locality_value):
        return {
            'name': 'Piazza del Colosseo',
            'address': {
                'ISO3166-2-lvl4': self.region.id,
                'ISO3166-1': 'IT',
                'city': locality_value,
            },
        }

    def test_exact_city_name_wins_over_substring_decoy(self):
        result = extractIsoCode(self.user, self._geocode_data('Rome'))
        self.assertEqual(result['city'], 'Rome')

    def test_nominatim_roma_spelling_does_not_match_arcinazzo_romano(self):
        # Nominatim returns the Italian spelling "Roma"; it should not fall through
        # to a name__icontains match against "Arcinazzo Romano".
        result = extractIsoCode(self.user, self._geocode_data('Roma'))
        self.assertNotEqual(result['city'], 'Arcinazzo Romano')
