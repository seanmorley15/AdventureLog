import importlib
import io
import json
import zipfile
from datetime import date

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionItineraryDay

set_collection_types = importlib.import_module(
    'adventures.migrations.0077_collection_type'
).set_collection_types
from adventures.utils.collection_type import BACKUP_SCHEMA, assign_collection_type_from_dates
from users.models import CustomUser


class _SchemaEditor:
    connection = connection


class CollectionTypeMigrationTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='type-migration-user',
            email='type-migration@example.com',
            password='testpassword123',
        )

    def test_dates_map_to_type_without_touching_itinerary(self):
        both = Collection.objects.create(
            user=self.user,
            name='Both dates',
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 10),
            type='folder',
        )
        year = Collection.objects.create(
            user=self.user,
            name='Year album',
            start_date=date(2019, 1, 1),
            end_date=date(2019, 12, 31),
            type='folder',
        )
        neither = Collection.objects.create(
            user=self.user,
            name='Neither date',
            type='trip',
        )
        one_date = Collection.objects.create(
            user=self.user,
            name='One date',
            start_date=date(2021, 6, 1),
            type='trip',
        )
        day = CollectionItineraryDay.objects.create(
            collection=year,
            date=date(2019, 1, 1),
            name='New Year',
        )
        day_count = CollectionItineraryDay.objects.count()

        set_collection_types(apps, _SchemaEditor())

        both.refresh_from_db()
        year.refresh_from_db()
        neither.refresh_from_db()
        one_date.refresh_from_db()
        day.refresh_from_db()

        self.assertEqual(both.type, 'trip')
        self.assertEqual(both.start_date, date(2020, 1, 1))
        self.assertEqual(both.end_date, date(2020, 1, 10))
        self.assertEqual(year.type, 'trip')
        self.assertEqual(year.start_date, date(2019, 1, 1))
        self.assertEqual(year.end_date, date(2019, 12, 31))
        self.assertEqual(neither.type, 'folder')
        self.assertIsNone(neither.start_date)
        self.assertIsNone(neither.end_date)
        self.assertEqual(one_date.type, 'folder')
        self.assertEqual(one_date.start_date, date(2021, 6, 1))
        self.assertIsNone(one_date.end_date)
        self.assertEqual(CollectionItineraryDay.objects.count(), day_count)
        self.assertEqual(day.name, 'New Year')
        self.assertEqual(day.date, date(2019, 1, 1))

    def test_type_from_dates_ignores_span_length(self):
        self.assertEqual(
            assign_collection_type_from_dates(date(2024, 1, 1), date(2024, 12, 31)),
            'trip',
        )
        self.assertEqual(assign_collection_type_from_dates(None, None), 'folder')
        self.assertEqual(assign_collection_type_from_dates(date(2024, 1, 1), None), 'folder')
        self.assertEqual(assign_collection_type_from_dates(None, date(2024, 1, 1)), 'folder')


class CollectionTypeApiTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='type-api-user',
            email='type-api@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(user=self.user)

    def test_create_trip_and_folder_store_type(self):
        trip = self.client.post(
            '/api/collections/',
            {
                'name': 'Weekend',
                'type': 'trip',
                'start_date': '2026-11-01',
                'end_date': '2026-11-03',
            },
            format='json',
        )
        self.assertEqual(trip.status_code, 201, trip.content)
        self.assertEqual(trip.json()['type'], 'trip')
        self.assertEqual(trip.json()['status'], 'upcoming')

        folder = self.client.post(
            '/api/collections/',
            {'name': 'Ideas', 'type': 'folder'},
            format='json',
        )
        self.assertEqual(folder.status_code, 201, folder.content)
        self.assertEqual(folder.json()['type'], 'folder')
        self.assertIsNone(folder.json()['status'])
        self.assertIsNone(folder.json()['start_date'])
        self.assertIsNone(folder.json()['end_date'])

        stored_trip = Collection.objects.get(id=trip.json()['id'])
        stored_folder = Collection.objects.get(id=folder.json()['id'])
        self.assertEqual(stored_trip.type, 'trip')
        self.assertEqual(stored_folder.type, 'folder')
        # A trip of 21 days or fewer is built as days; a folder never is.
        self.assertEqual(stored_trip.itinerary_days.filter(index__isnull=False).count(), 3)
        self.assertEqual(stored_folder.itinerary_days.count(), 0)

    def test_trip_requires_both_dates(self):
        response = self.client.post(
            '/api/collections/',
            {'name': 'Half trip', 'type': 'trip', 'start_date': '2026-11-01'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_old_client_omits_type(self):
        both = self.client.post(
            '/api/collections/',
            {
                'name': 'Dated',
                'start_date': '2026-04-01',
                'end_date': '2026-04-08',
            },
            format='json',
        )
        self.assertEqual(both.status_code, 201, both.content)
        self.assertEqual(both.json()['type'], 'trip')
        self.assertNotEqual(both.json()['status'], 'folder')

        neither = self.client.post(
            '/api/collections/',
            {'name': 'Undated'},
            format='json',
        )
        self.assertEqual(neither.status_code, 201, neither.content)
        self.assertEqual(neither.json()['type'], 'folder')
        self.assertIsNone(neither.json()['status'])

        one = self.client.post(
            '/api/collections/',
            {'name': 'Start only', 'start_date': '2026-05-01'},
            format='json',
        )
        self.assertEqual(one.status_code, 201, one.content)
        self.assertEqual(one.json()['type'], 'folder')
        self.assertEqual(one.json()['start_date'], '2026-05-01')
        self.assertIsNone(one.json()['end_date'])
        self.assertIsNone(one.json()['status'])

    def test_range_over_21_days_is_a_trip_without_day_rows(self):
        response = self.client.post(
            '/api/collections/',
            {
                'name': 'Year',
                'start_date': '2026-01-01',
                'end_date': '2026-12-31',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['type'], 'trip')
        collection = Collection.objects.get(id=response.json()['id'])
        self.assertGreater((collection.end_date - collection.start_date).days, 21)
        self.assertEqual(collection.itinerary_days.count(), 0)
        self.assertEqual(collection.itinerary_items.count(), 0)

    def test_list_filter_uses_type_not_status_folder(self):
        self.client.post(
            '/api/collections/',
            {'name': 'Folder A', 'type': 'folder'},
            format='json',
        )
        self.client.post(
            '/api/collections/',
            {
                'name': 'Trip A',
                'type': 'trip',
                'start_date': '2026-08-01',
                'end_date': '2026-08-10',
            },
            format='json',
        )

        folders = self.client.get('/api/collections/?type=folder')
        self.assertEqual(folders.status_code, 200)
        names = [item['name'] for item in folders.json()['results']]
        self.assertEqual(names, ['Folder A'])
        self.assertTrue(all(item['type'] == 'folder' for item in folders.json()['results']))
        self.assertTrue(all(item['status'] != 'folder' for item in folders.json()['results']))

        by_old_status = self.client.get('/api/collections/?status=folder')
        self.assertEqual(by_old_status.status_code, 200)
        old_names = {item['name'] for item in by_old_status.json()['results']}
        self.assertIn('Folder A', old_names)
        self.assertIn('Trip A', old_names)

    def test_folder_can_keep_one_date(self):
        response = self.client.post(
            '/api/collections/',
            {
                'name': 'Loose folder',
                'type': 'folder',
                'end_date': '2026-09-01',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['type'], 'folder')
        self.assertIsNone(response.json()['start_date'])
        self.assertEqual(response.json()['end_date'], '2026-09-01')


class CollectionTypeBackupTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='type-backup-user',
            email='type-backup@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(user=self.user)

    def _zip_with(self, payload):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zipf:
            zipf.writestr('data.json', json.dumps(payload))
        buffer.seek(0)
        return SimpleUploadedFile('backup.zip', buffer.read(), content_type='application/zip')

    def _import(self, payload):
        return self.client.post(
            '/api/backup/import/',
            {'file': self._zip_with(payload), 'confirm': 'yes'},
            format='multipart',
        )

    def test_backup_round_trip_keeps_type(self):
        self.client.post(
            '/api/collections/',
            {
                'name': 'Kept trip',
                'type': 'trip',
                'start_date': '2027-01-01',
                'end_date': '2027-01-20',
            },
            format='json',
        )
        self.client.post(
            '/api/collections/',
            {'name': 'Kept folder', 'type': 'folder'},
            format='json',
        )

        exported = self.client.get('/api/backup/export/')
        self.assertEqual(exported.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(exported.content)) as zipf:
            data = json.loads(zipf.read('data.json').decode('utf-8'))

        self.assertEqual(data['backup_schema'], BACKUP_SCHEMA)
        self.assertIn('version', data)
        types = {item['name']: item['type'] for item in data['collections']}
        self.assertEqual(types['Kept trip'], 'trip')
        self.assertEqual(types['Kept folder'], 'folder')

        imported = self.client.post(
            '/api/backup/import/',
            {
                'file': SimpleUploadedFile('backup.zip', exported.content, content_type='application/zip'),
                'confirm': 'yes',
            },
            format='multipart',
        )
        self.assertEqual(imported.status_code, 200, imported.content)
        restored = {
            collection.name: collection.type
            for collection in Collection.objects.filter(user=self.user)
        }
        self.assertEqual(restored['Kept trip'], 'trip')
        self.assertEqual(restored['Kept folder'], 'folder')

    def test_missing_schema_sets_type_from_dates_and_keeps_a_long_range(self):
        response = self._import({
            'version': 'v0.12.0',
            'collections': [
                {
                    'export_id': 0,
                    'name': 'Old trip',
                    'start_date': '2018-01-01',
                    'end_date': '2018-12-31',
                },
                {
                    'export_id': 1,
                    'name': 'Old folder',
                },
                {
                    'export_id': 2,
                    'name': 'Old one date',
                    'start_date': '2018-06-01',
                },
            ],
        })
        self.assertEqual(response.status_code, 200, response.content)
        restored = {c.name: c for c in Collection.objects.filter(user=self.user)}
        self.assertEqual(restored['Old trip'].type, 'trip')
        self.assertEqual(restored['Old trip'].start_date, date(2018, 1, 1))
        self.assertEqual(restored['Old trip'].end_date, date(2018, 12, 31))
        self.assertGreater(
            (restored['Old trip'].end_date - restored['Old trip'].start_date).days,
            21,
        )
        self.assertEqual(restored['Old trip'].itinerary_days.count(), 0)
        self.assertEqual(restored['Old folder'].type, 'folder')
        self.assertEqual(restored['Old one date'].type, 'folder')
        self.assertEqual(restored['Old one date'].start_date, date(2018, 6, 1))
        self.assertIsNone(restored['Old one date'].end_date)

    def test_newer_schema_is_rejected_without_clearing_data(self):
        existing = Collection.objects.create(user=self.user, name='Stay', type='folder')
        response = self._import({
            'backup_schema': BACKUP_SCHEMA + 1,
            'version': 'v9.9.9',
            'collections': [
                {
                    'export_id': 0,
                    'name': 'From the future',
                    'type': 'trip',
                    'start_date': '2030-01-01',
                    'end_date': '2030-01-05',
                    'unknown_key': {'keep': True},
                }
            ],
        })
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Collection.objects.filter(id=existing.id, name='Stay').exists())
        self.assertFalse(Collection.objects.filter(name='From the future').exists())

    def test_schema_2_keeps_explicit_type(self):
        response = self._import({
            'backup_schema': 2,
            'version': 'v0.13.0',
            'collections': [
                {
                    'export_id': 0,
                    'name': 'Folder with dates',
                    'type': 'folder',
                    'start_date': '2025-01-01',
                    'end_date': '2025-01-03',
                }
            ],
        })
        self.assertEqual(response.status_code, 200, response.content)
        collection = Collection.objects.get(user=self.user, name='Folder with dates')
        self.assertEqual(collection.type, 'folder')
        self.assertEqual(collection.start_date, date(2025, 1, 1))
        self.assertEqual(collection.end_date, date(2025, 1, 3))
