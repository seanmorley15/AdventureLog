from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from adventures.models import Category, Location, Visit
from adventures.services import travelers
from adventures.services.calendar_events import get_calendar_events_for_user
from adventures.services.dashboard import build_dashboard_data
from adventures.services.exports.pdf import PdfOptions, build_collection_pdf, get_collection_for_pdf
from adventures.services.exports.pdf.data import visit_info
from adventures.services.geocoding.assignment import geocode_and_assign_location
from adventures.services.user_stats import UserStatsService
from adventures.services.visited_regions import sync_visited_regions
from adventures.tests.base import AudienceTestBase
from core.geo import make_point
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion


def _past():
    return datetime(2026, 6, 1, 10, 0, tzinfo=dt_timezone.utc)


class CountingTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.visit = Visit.objects.create(location=self.hut, start_date=_past(), end_date=_past() + timedelta(days=1))
        self.visit.travelers.set([self.owner, self.editor])
        self.country = Country.objects.create(name='Norway', country_code='NO', coordinates=make_point(8, 61))
        self.region = Region.objects.create(id='NO-18', name='Nordland', country=self.country)
        self.city = City.objects.create(id='NO-18-1', name='Reine', region=self.region, coordinates=make_point(13.0, 67.9))

    def test_editor_list_includes_hut_visited(self):
        self.as_user(self.editor)
        body = self.client.get('/api/locations/').json()
        rows = {row['id']: row for row in body['results']}
        self.assertIn(str(self.hut.id), rows)
        self.assertTrue(rows[str(self.hut.id)]['is_visited'])
        self.assertEqual(body['visited_count'], 1)

    def test_editor_pins_include_hut(self):
        self.as_user(self.editor)
        pins = {row['id']: row for row in self.client.get('/api/locations/pins/').json()}
        self.assertTrue(pins[str(self.hut.id)]['is_visited'])

    def test_non_traveling_member_pin_not_visited(self):
        self.as_user(self.viewer)
        pins = self.client.get('/api/locations/pins/').json()
        self.assertEqual(pins, [])

    def test_editor_stats_count_hut(self):
        self.assertEqual(UserStatsService().get_visited_locations_count(self.editor), 1)

    def test_editor_dashboard_recent_has_hut(self):
        data = build_dashboard_data(self.editor, self.editor)
        self.assertEqual([row['id'] for row in data['recent_locations']], [str(self.hut.id)])

    def test_editor_calendar_has_visit_event(self):
        events = get_calendar_events_for_user(self.editor, start='2026-05-30', end='2026-06-05', types='visit')
        self.assertEqual([e['resource_id'] for e in events], [str(self.hut.id)])

    def test_geocode_marks_region_for_each_traveler(self):
        self.hut.coordinates = make_point(13.0, 67.9)
        self.hut.save(update_fields=['coordinates'], _skip_geocode=True)
        result = SimpleNamespace(data={'region_id': self.region.id, 'city_id': self.city.id})
        with patch('adventures.services.geocoding.assignment.reverse_geocode_service', return_value=result):
            geocode_and_assign_location(str(self.hut.id))
        for user in (self.owner, self.editor):
            self.assertTrue(VisitedRegion.objects.filter(user=user, region=self.region).exists())
            self.assertTrue(VisitedCity.objects.filter(user=user, city=self.city).exists())
        self.assertFalse(VisitedRegion.objects.filter(user=self.viewer).exists())

    def test_sync_visited_regions_uses_traveled(self):
        Location.objects.filter(pk=self.hut.pk).update(region=self.region)
        sync_visited_regions(self.editor)
        self.assertTrue(VisitedRegion.objects.filter(user=self.editor, region=self.region).exists())
        sync_visited_regions(self.viewer)
        self.assertFalse(VisitedRegion.objects.filter(user=self.viewer).exists())

    def test_traveled_place_outside_membership_not_listed(self):
        self.hut.collections.remove(self.trip)
        self.as_user(self.editor)
        ids = [row['id'] for row in self.client.get('/api/locations/').json()['results']]
        self.assertNotIn(str(self.hut.id), ids)
        pins = [row['id'] for row in self.client.get('/api/locations/pins/').json()]
        self.assertNotIn(str(self.hut.id), pins)

    def test_category_filter_includes_traveled_by_name(self):
        theirs = Category.objects.create(user=self.owner, name='hiking', display_name='Hiking', icon='x')
        Location.objects.filter(pk=self.hut.pk).update(category=theirs)
        own = Category.objects.create(user=self.editor, name='hiking', display_name='Hiking', icon='x')
        mine = Location.objects.create(user=self.editor, name='Mine', category=own)
        other = Location.objects.create(user=self.editor, name='Other')
        self.as_user(self.editor)
        ids = {row['id'] for row in self.client.get('/api/locations/?category=hiking').json()['results']}
        self.assertEqual(ids, {str(self.hut.id), str(mine.id)})
        self.assertNotIn(str(other.id), ids)

    def test_public_profile_unchanged(self):
        Location.objects.filter(pk=self.hut.pk).update(is_public=True)
        self.as_user(self.stranger)
        body = self.client.get(f'/api/users/{self.editor.username}/locations/')
        self.assertEqual(body.status_code, 200)
        self.assertEqual(body.json()['results'], [])

    def test_pdf_marks_visited_for_exporter(self):
        hut = Location.objects.prefetch_related('visits__travelers').get(pk=self.hut.pk)
        self.assertTrue(visit_info(hut, self.editor)[0])
        self.assertFalse(visit_info(hut, self.viewer)[0])
        self.assertTrue(visit_info(hut)[0])
        collection = get_collection_for_pdf(self.trip.id)
        pdf = build_collection_pdf(collection, options=PdfOptions(), viewer=self.editor)
        self.assertTrue(pdf.startswith(b'%PDF'))


class ListQueryCountTests(AudienceTestBase):
    def _add(self, count):
        for index in range(count):
            place = Location.objects.create(user=self.owner, name=f'Extra {Location.objects.count()}')
            place.collections.add(self.trip)
            visit = Visit.objects.create(location=place, start_date=_past())
            visit.travelers.set([self.owner, self.editor])

    def _queries(self, url):
        self.client.get(url)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(queries)

    def test_list_and_pins_do_not_query_per_row(self):
        self.as_user(self.editor)
        self._add(2)
        few = {url: self._queries(url) for url in ('/api/locations/', '/api/locations/pins/')}
        self._add(8)
        for url, count in few.items():
            self.assertEqual(self._queries(url), count, url)
