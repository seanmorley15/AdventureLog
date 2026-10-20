import io
import json
import zipfile
from datetime import timedelta
from io import StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import Location, Visit
from adventures.utils.collection_type import BACKUP_SCHEMA
from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion


class VisitedGeographyFlowTests(APITestCase):
    """The flows that turn locations or backups into VisitedRegion/VisitedCity rows."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geo-user', email='geo-user@example.com', password='testpassword123'
        )
        country = Country.objects.create(name='France', country_code='FR', coordinates=make_point(2.2, 46.2))
        self.region = Region.objects.create(id='FR-IDF', name='Ile-de-France', country=country)
        self.city = City.objects.create(id='FR-IDF-1', name='Paris', region=self.region)
        self.client.force_authenticate(user=self.user)

        now = timezone.now()
        self.visited = Location.objects.create(
            user=self.user, name='Louvre', region=self.region, city=self.city, country=country
        )
        Visit.objects.create(location=self.visited, start_date=now - timedelta(days=3), end_date=now - timedelta(days=2))
        # Planned only: no visit, so it must not count as visited.
        other_region = Region.objects.create(id='FR-BRE', name='Bretagne', country=country)
        self.planned = Location.objects.create(user=self.user, name='Brest', region=other_region)

    def test_mark_visited_region_endpoint_marks_only_visited_locations(self):
        response = self.client.post('/api/reverse-geocode/mark_visited_region/')

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body['new_regions'], 1)
        self.assertEqual(body['regions'], {'FR-IDF': 'Ile-de-France'})
        self.assertEqual(body['new_cities'], 1)
        self.assertEqual(body['cities'], {'FR-IDF-1': 'Paris'})
        self.assertEqual(list(VisitedRegion.objects.values_list('region_id', flat=True)), ['FR-IDF'])

    def test_mark_visited_region_endpoint_is_idempotent(self):
        self.client.post('/api/reverse-geocode/mark_visited_region/')

        response = self.client.post('/api/reverse-geocode/mark_visited_region/')

        self.assertEqual(response.json()['new_regions'], 0)
        self.assertEqual(response.json()['new_cities'], 0)
        self.assertEqual(VisitedRegion.objects.count(), 1)
        self.assertEqual(VisitedCity.objects.count(), 1)

    def test_sync_command_dry_run_writes_nothing(self):
        out = StringIO()
        call_command('sync_visited_regions', '--dry-run', stdout=out)

        self.assertIn('Would create 1 new visited regions', out.getvalue())
        self.assertFalse(VisitedRegion.objects.exists())

    def test_sync_command_creates_rows_once(self):
        call_command('sync_visited_regions', stdout=StringIO())
        out = StringIO()
        call_command('sync_visited_regions', stdout=out)

        self.assertEqual(VisitedRegion.objects.filter(user=self.user).count(), 1)
        self.assertEqual(VisitedCity.objects.filter(user=self.user).count(), 1)
        self.assertIn('Created 0 new visited regions', out.getvalue())

    def test_backup_import_restores_visited_regions_and_cities_without_duplicates(self):
        backup = {
            'backup_schema': BACKUP_SCHEMA,
            'collections': [],
            'locations': [],
            'visited_regions': [{'region': 'FR-IDF'}, {'region': 'FR-IDF'}, {'region': 'XX-NOPE'}],
            'visited_cities': [{'city': 'FR-IDF-1'}, {'city': 'XX-NOPE'}],
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('data.json', json.dumps(backup))
        upload = SimpleUploadedFile('backup.zip', buffer.getvalue(), content_type='application/zip')

        response = self.client.post('/api/backup/import/', {'file': upload, 'confirm': 'yes'}, format='multipart')

        self.assertEqual(response.status_code, 200, response.content)
        summary = response.json()['summary']
        self.assertEqual(summary['visited_regions'], 1)
        self.assertEqual(summary['visited_cities'], 1)
        self.assertEqual(VisitedRegion.objects.filter(user=self.user).count(), 1)
        self.assertEqual(VisitedCity.objects.filter(user=self.user).count(), 1)

    def test_visiting_a_city_through_the_api_also_marks_its_region(self):
        response = self.client.post('/api/visitedcity/', {'city': 'FR-IDF-1'}, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(VisitedRegion.objects.filter(user=self.user, region=self.region).exists())
