from datetime import date, timedelta
from unittest.mock import patch
import shutil
import tempfile

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import Activity, Category, Collection, Location, Lodging, Note, Visit, CollectionItineraryItem, ContentAttachment, ContentImage, Transportation
from adventures.serializers import TransportationSerializer
from adventures.services.day_plan import convert_collection, get_day_by_index, place_object
from adventures.tests.base import make_user
from core.geo import make_point
from integrations.models import ImmichIntegration
from users.models import CustomUser
from worldtravel.models import Country, Region, VisitedRegion, City


def count_queries(call):
    with CaptureQueriesContext(connection) as queries:
        result = call()
    return len(queries), result


class QueryCountTestBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = CustomUser.objects.create_user(
            username='counts-user', email='counts-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)


class ItineraryListQueryTests(QueryCountTestBase):
    def add_items(self, trip, count):
        kinds = [Location, Lodging, Note]
        for index in range(count):
            model = kinds[index % len(kinds)]
            obj = model.objects.create(user=self.user, name=f'Stop {trip.itinerary_items.count()} {index}')
            CollectionItineraryItem.objects.create(
                collection=trip,
                content_type=ContentType.objects.get_for_model(model),
                object_id=obj.id,
                is_global=True,
                order=trip.itinerary_items.count(),
            )

    def test_listing_items_does_not_query_once_per_item(self):
        trip = Collection.objects.create(user=self.user, name='Trip')
        self.add_items(trip, 3)
        self.client.get('/api/itineraries/')
        few, response = count_queries(lambda: self.client.get('/api/itineraries/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

        self.add_items(trip, 9)
        many, response = count_queries(lambda: self.client.get('/api/itineraries/'))
        self.assertEqual(len(response.json()), 12)

        self.assertEqual(few, many)

    def test_a_deleted_target_still_serializes_as_no_item(self):
        trip = Collection.objects.create(user=self.user, name='Trip')
        place = Location.objects.create(user=self.user, name='Gone soon')
        item = CollectionItineraryItem.objects.create(
            collection=trip,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=place.id,
            is_global=True,
            order=0,
        )
        # A row left behind by older versions: delete the target without the signal's cleanup.
        Location.objects.filter(pk=place.pk)._raw_delete(Location.objects.db)

        response = self.client.get('/api/itineraries/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.json()], [str(item.id)])
        self.assertIsNone(response.json()[0]['item'])


class MapPinQueryTests(QueryCountTestBase):
    def test_map_pins_query_count_does_not_grow_with_photos(self):
        ImmichIntegration.objects.create(user=self.user, server_url='http://immich.example.com/api', api_key='k')

        def add_photos(count):
            for index in range(count):
                place = Location.objects.create(user=self.user, name=f'Place {Location.objects.count()}')
                ContentImage.objects.create(
                    user=self.user,
                    content_type=ContentType.objects.get_for_model(Location),
                    object_id=place.id,
                    immich_id=f'asset-{place.id}',
                    source=ContentImage.Source.IMMICH,
                    coordinates=make_point(10.0 + index, 50.0),
                )

        add_photos(2)
        self.client.get('/api/images/map_pins/')  # warm Django's ContentType cache
        few, response = count_queries(lambda: self.client.get('/api/images/map_pins/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        add_photos(8)
        many, response = count_queries(lambda: self.client.get('/api/images/map_pins/'))
        self.assertEqual(len(response.json()), 10)

        self.assertEqual(few, many)
        self.assertEqual(response.json()[0]['parent_type'], 'location')
        self.assertTrue(response.json()[0]['parent_name'].startswith('Place'))


class TransportDistanceTests(QueryCountTestBase):
    def setUp(self):
        super().setUp()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)

    def add_transport(self, with_gpx=True):
        transport = Transportation.objects.create(
            user=self.user, name='Train', type='train',
            origin=make_point(2.35, 48.85), destination=make_point(4.83, 45.76),
        )
        if with_gpx:
            attachment = ContentAttachment(
                user=self.user,
                content_type=ContentType.objects.get_for_model(Transportation),
                object_id=transport.id,
                name='route',
            )
            attachment.file.save('route.gpx', ContentFile(b'<gpx/>'), save=True)
        return transport

    def test_gpx_distance_is_parsed_once_per_file(self):
        transport = self.add_transport()
        with patch.object(TransportationSerializer, '_parse_gpx_distance_km', return_value=12.34) as parse:
            first = TransportationSerializer(transport).data['distance']
            second = TransportationSerializer(transport).data['distance']

        self.assertEqual((first, second), (12.34, 12.34))
        self.assertEqual(parse.call_count, 1)

    def test_a_failed_parse_is_not_cached_and_falls_back_to_the_straight_line(self):
        transport = self.add_transport()
        with patch.object(TransportationSerializer, '_parse_gpx_distance_km', return_value=None) as parse:
            distance = TransportationSerializer(transport).data['distance']
            TransportationSerializer(transport).data

        self.assertGreater(distance, 300)
        self.assertEqual(parse.call_count, 2)

    def test_transport_without_gpx_uses_the_straight_line(self):
        transport = self.add_transport(with_gpx=False)

        self.assertGreater(TransportationSerializer(transport).data['distance'], 300)

    def test_transport_list_query_count_does_not_grow_with_rows(self):
        self.add_transport()
        self.client.get('/api/transportations/')
        few, response = count_queries(lambda: self.client.get('/api/transportations/'))
        self.assertEqual(len(response.json()), 1)

        with patch.object(TransportationSerializer, '_parse_gpx_distance_km', return_value=5.0):
            for _ in range(6):
                self.add_transport()
            many, response = count_queries(lambda: self.client.get('/api/transportations/'))
        self.assertEqual(len(response.json()), 7)

        self.assertEqual(few, many)


class DashboardQueryTests(QueryCountTestBase):
    def setUp(self):
        super().setUp()
        country = Country.objects.create(name='France', country_code='FR')
        region = Region.objects.create(id='FR-75', name='Paris Region', country=country)
        self.city = City.objects.create(id='FR-75-paris', name='Paris', region=region)
        self.country, self.region = country, region

    def add_recent_place(self, index):
        place = Location.objects.create(
            user=self.user, name=f'Place {index}', country=self.country, region=self.region, city=self.city
        )
        for offset in (3, 9):
            visit = Visit.objects.create(location=place, start_date=timezone.now() - timedelta(days=offset + index))
            Activity.objects.create(user=self.user, visit=visit, name=f'Walk {index}-{offset}')
        return place

    def add_trip(self, index):
        today = date.today()
        return Collection.objects.create(
            user=self.user, name=f'Trip {index}', type='trip',
            start_date=today + timedelta(days=5 + index), end_date=today + timedelta(days=8 + index),
        )

    def test_dashboard_query_count_does_not_grow_with_places_or_trips(self):
        self.add_recent_place(0)
        self.add_trip(0)
        self.client.get('/api/stats/dashboard/')
        few, response = count_queries(lambda: self.client.get('/api/stats/dashboard/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['recent_locations']), 1)

        for index in range(1, 3):
            self.add_recent_place(index)
            self.add_trip(index)
        many, response = count_queries(lambda: self.client.get('/api/stats/dashboard/'))
        data = response.json()
        self.assertEqual(len(data['recent_locations']), 3)
        self.assertEqual(len(data['upcoming_trips']), 3)

        self.assertEqual(few, many)
        # The counts a card shows still come through the annotation.
        self.assertTrue(all('location_count' in trip for trip in data['upcoming_trips']))


class QueryCountTests(APITestCase):
    """Query counts stay flat as the amount of data grows."""

    def setUp(self):
        cache.clear()
        self.user = make_user('perf')
        self.client.force_authenticate(user=self.user)
        self.trip = Collection.objects.create(
            user=self.user, name='Trip', type='trip',
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 4),
        )
        convert_collection(self.trip)
        self.country = Country.objects.create(name='Norway', country_code='NO')
        self.region = Region.objects.create(id='NO-03', name='Oslo', country=self.country)

    def add_places(self, n, start=0):
        location_ct = ContentType.objects.get_for_model(Location)
        for i in range(start, start + n):
            category = Category.objects.get_or_create(
                user=self.user, name=f'cat{i % 3}', defaults={'display_name': f'Cat {i % 3}', 'icon': '*'}
            )[0]
            place = Location.objects.create(
                user=self.user, name=f'Place {i}', category=category,
                country=self.country, region=self.region,
            )
            place.collections.add(self.trip)
            Visit.objects.create(
                location=place,
                start_date=timezone.make_aware(timezone.datetime(2026, 6, 2)),
                end_date=timezone.make_aware(timezone.datetime(2026, 6, 2)),
            )
            place_object(self.trip, location_ct, place.id, day=get_day_by_index(self.trip, 1 + i % 3))
            Lodging.objects.create(user=self.user, name=f'Stay {i}', collection=self.trip)
            Note.objects.create(user=self.user, name=f'Note {i}', collection=self.trip)

    def get(self, url, **params):
        return self.client.get(url, params)

    def assert_flat(self, url, label, slack=3, **params):
        self.add_places(4)
        small, response = count_queries(lambda: self.get(url, **params))
        self.assertEqual(response.status_code, 200, label)
        self.add_places(12, start=4)
        large, response = count_queries(lambda: self.get(url, **params))
        self.assertEqual(response.status_code, 200, label)
        self.assertLessEqual(large, small + slack, f'{label}: {small} queries for 4 places, {large} for 16')
        return large

    def test_collection_detail_does_not_grow_with_places(self):
        self.assert_flat(f'/api/collections/{self.trip.id}/', 'collection detail')

    def test_story_does_not_grow_with_places(self):
        self.trip.visibility = 'public'
        self.trip.save()
        self.client.force_authenticate(user=None)
        self.assert_flat(f'/api/collections/{self.trip.id}/', 'story')

    def test_location_list_all_and_pins_do_not_grow(self):
        self.assert_flat('/api/locations/', 'locations list')
        self.assert_flat('/api/locations/all/', 'locations all', include_collections='true')
        self.assert_flat('/api/locations/pins/', 'pins')

    def test_collection_lists_do_not_grow_with_collections(self):
        def make(n, start):
            for i in range(start, start + n):
                c = Collection.objects.create(user=self.user, name=f'C{i}', type='trip')
                convert_collection(c)
                c.shared_with.add(make_user(f'friend{i}'))
        make(3, 0)
        small, _ = count_queries(lambda: self.get('/api/collections/'))
        make(9, 3)
        large, response = count_queries(lambda: self.get('/api/collections/'))
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(large, small + 3, f'{small} vs {large}')

    def test_calendar_does_not_grow(self):
        self.assert_flat('/api/calendar/events/', 'calendar')

    def test_categories_do_not_grow(self):
        self.assert_flat('/api/categories/', 'categories')

    def test_world_travel_counts_match_and_do_not_grow(self):
        for i in range(3):
            region = Region.objects.create(id=f'NO-{50 + i}', name=f'R{i}', country=self.country)
            VisitedRegion.objects.create(user=self.user, region=region)
        data = self.get('/api/countries/').json()
        results = data['results'] if isinstance(data, dict) and 'results' in data else data
        norway = next(c for c in results if c['country_code'] == 'NO')
        self.assertEqual(norway['num_regions'], Region.objects.filter(country=self.country).count())
        self.assertEqual(norway['num_visits'], 3)
        for i in range(30):
            Country.objects.create(name=f'Land {i}', country_code=f'{chr(65 + i // 26)}{chr(65 + i % 26)}'.replace('NO', 'NX'))
        n, _ = count_queries(lambda: self.get('/api/countries/'))
        self.assertLessEqual(n, 6)


class CurrentUserCountsTests(APITestCase):
    def test_current_user_returns_badge_counts(self):
        user = make_user('badge')
        owner = make_user('badge-owner')
        trip = Collection.objects.create(user=owner, name='Shared')
        from adventures.models import CollectionInvite

        CollectionInvite.objects.create(collection=trip, invited_user=user)
        self.client.force_authenticate(user=user)
        body = self.client.get('/auth/current-user/').json()
        self.assertEqual(body['pending_invite_count'], 1)
        self.assertEqual(body['unread_comment_count'], 0)
