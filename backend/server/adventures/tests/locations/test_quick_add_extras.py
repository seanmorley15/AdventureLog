from datetime import date
from unittest.mock import patch

from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionItineraryItem, Location, Lodging
from adventures.services.day_plan import convert_collection
from users.models import CustomUser

FAILED_PHOTO = {'url': 'http://example.com/a.jpg', 'error': 'Could not fetch'}
IMPORT_SUMMARY = {
    'created_images': [],
    'results': [],
    'created_count': 1,
    'requested_count': 2,
    'failed_count': 1,
    'failed': [FAILED_PHOTO],
}


@patch('adventures.services.quick_add.import_remote_images_for_object', return_value=IMPORT_SUMMARY)
class QuickAddExtrasTests(APITestCase):
    """Location and lodging quick add share how photos and placements are reported."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='extras-user', email='extras-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)
        self.trip = Collection.objects.create(
            user=self.user, name='Trip', type='trip', start_date=date(2026, 6, 1), end_date=date(2026, 6, 3)
        )
        convert_collection(self.trip)
        for patcher in (
            patch('adventures.services.quick_add.reverse_geocode_service', return_value=None),
            patch('adventures.services.quick_add.extract_google_place_details', return_value=({}, {})),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def payload(self, **extra):
        return {'name': 'Hut', 'latitude': 67.9, 'longitude': 13.0, **extra}

    def test_location_reports_failed_photos_and_its_placement(self, import_photos):
        response = self.client.post(
            '/api/locations/quick-add/',
            self.payload(
                collection_id=str(self.trip.id), itinerary_date='2026-06-02',
                photos=['http://example.com/a.jpg', 'http://example.com/b.jpg'],
            ),
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['quick_add_image_import'], {'created_count': 1, 'failed_count': 1, 'failed': [FAILED_PHOTO]})
        self.assertEqual(body['quick_add_itinerary_item']['content_type'], 'location')
        self.assertEqual(CollectionItineraryItem.objects.filter(collection=self.trip).count(), 1)
        self.assertEqual(import_photos.call_args.kwargs['explicit_source'], 'google')
        self.assertEqual(import_photos.call_args.args[0], Location.objects.get(id=body['id']))

    def test_lodging_reports_failed_photos_and_its_placement(self, import_photos):
        response = self.client.post(
            '/api/lodging/quick-add/',
            self.payload(
                collection_id=str(self.trip.id), itinerary_date='2026-06-02',
                photos=['http://example.com/a.jpg', 'http://example.com/b.jpg'],
            ),
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['quick_add_image_import'], {'created_count': 1, 'failed_count': 1, 'failed': [FAILED_PHOTO]})
        self.assertEqual(body['quick_add_itinerary_item']['content_type'], 'lodging')
        self.assertEqual(import_photos.call_args.args[0], Lodging.objects.get(id=body['id']))

    def test_no_photos_and_no_date_adds_no_extras(self, import_photos):
        for url in ('/api/locations/quick-add/', '/api/lodging/quick-add/'):
            response = self.client.post(url, self.payload(), format='json')

            self.assertEqual(response.status_code, 201, response.content)
            self.assertNotIn('quick_add_image_import', response.json())
            self.assertNotIn('quick_add_itinerary_item', response.json())
        import_photos.assert_not_called()

    def test_photos_that_all_import_leave_no_failure_note(self, import_photos):
        import_photos.return_value = {**IMPORT_SUMMARY, 'failed': [], 'failed_count': 0}

        response = self.client.post(
            '/api/locations/quick-add/', self.payload(photos=['http://example.com/a.jpg']), format='json'
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertNotIn('quick_add_image_import', response.json())

    def test_a_date_outside_the_trip_is_refused_for_both(self, import_photos):
        for url in ('/api/locations/quick-add/', '/api/lodging/quick-add/'):
            response = self.client.post(
                url, self.payload(collection_id=str(self.trip.id), itinerary_date='2027-01-01'), format='json'
            )

            self.assertEqual(response.status_code, 400, (url, response.content))
