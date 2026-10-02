import io
import json
import zipfile
from datetime import date, datetime, timezone

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from adventures.models import Checklist, ChecklistItem, Collection, Location, Lodging, Note, Transportation
from adventures.utils.geo import make_point, point_to_lat_lon
from users.models import CustomUser


class CollectionZipExportImportTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='zip-user',
            email='zip-user@example.com',
            password='testpassword123',
        )
        self.client.force_authenticate(user=self.user)
        self.collection = Collection.objects.create(
            user=self.user,
            name='Japan 2019',
            description='Cherry blossom trip',
            start_date=date(2019, 3, 20),
            end_date=date(2019, 3, 28),
            link='https://example.com/japan-2019',
        )
        self.location = Location(
            user=self.user,
            name='Fushimi Inari',
            description='Torii gates',
            location='Kyoto, Japan',
            coordinates=make_point(135.7727, 34.9671),
            is_public=False,
        )
        self.location.save(_skip_geocode=True)
        self.collection.locations.add(self.location)

        self.lodging = Lodging.objects.create(
            user=self.user,
            collection=self.collection,
            name='Kyoto Ryokan',
            type='hotel',
            description='Near Gion',
            check_in=datetime(2019, 3, 20, 15, 0, tzinfo=timezone.utc),
            check_out=datetime(2019, 3, 24, 10, 0, tzinfo=timezone.utc),
            timezone='Asia/Tokyo',
            reservation_number='KY-2019-1',
            coordinates=make_point(135.7681, 35.0116),
            location='Gion, Kyoto',
            is_public=False,
        )
        self.transport = Transportation.objects.create(
            user=self.user,
            collection=self.collection,
            type='train',
            name='Shinkansen to Kyoto',
            description='Tokyo to Kyoto',
            date=datetime(2019, 3, 20, 8, 0, tzinfo=timezone.utc),
            end_date=datetime(2019, 3, 20, 10, 15, tzinfo=timezone.utc),
            from_location='Tokyo',
            to_location='Kyoto',
            origin=make_point(139.7671, 35.6812),
            destination=make_point(135.7581, 34.9858),
            start_timezone='Asia/Tokyo',
            end_timezone='Asia/Tokyo',
            is_public=False,
        )
        self.note = Note.objects.create(
            user=self.user,
            collection=self.collection,
            name='Packing',
            content='Bring layers',
            date=date(2019, 3, 19),
            is_public=False,
        )
        self.checklist = Checklist.objects.create(
            user=self.user,
            collection=self.collection,
            name='Before departure',
            date=date(2019, 3, 18),
            is_public=False,
        )
        ChecklistItem.objects.create(
            user=self.user,
            checklist=self.checklist,
            name='Passport',
            is_checked=True,
        )

    def _export_metadata(self, collection_id=None):
        collection_id = collection_id or self.collection.id
        response = self.client.get(f'/api/collections/{collection_id}/export/')
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as zipf:
            return json.loads(zipf.read('metadata.json').decode('utf-8'))

    def _import_zip(self, metadata):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zipf:
            zipf.writestr('metadata.json', json.dumps(metadata))
        buffer.seek(0)
        upload = SimpleUploadedFile(
            'collection.zip',
            buffer.read(),
            content_type='application/zip',
        )
        return self.client.post(
            '/api/collections/import/',
            {'file': upload},
            format='multipart',
        )

    def test_export_includes_collection_dates_and_lodging_details(self):
        metadata = self._export_metadata()

        self.assertEqual(metadata['collection']['start_date'], '2019-03-20')
        self.assertEqual(metadata['collection']['end_date'], '2019-03-28')

        location = metadata['locations'][0]
        self.assertAlmostEqual(location['latitude'], 34.9671)
        self.assertAlmostEqual(location['longitude'], 135.7727)

        lodging = metadata['lodging'][0]
        self.assertEqual(lodging['name'], 'Kyoto Ryokan')
        self.assertEqual(lodging['type'], 'hotel')
        self.assertEqual(lodging['check_in'], '2019-03-20T15:00:00+00:00')
        self.assertEqual(lodging['check_out'], '2019-03-24T10:00:00+00:00')
        self.assertEqual(lodging['timezone'], 'Asia/Tokyo')
        self.assertAlmostEqual(lodging['latitude'], 35.0116)
        self.assertAlmostEqual(lodging['longitude'], 135.7681)
        self.assertEqual(lodging['location'], 'Gion, Kyoto')

        transport = metadata['transportation'][0]
        self.assertEqual(transport['type'], 'train')
        self.assertEqual(transport['date'], '2019-03-20T08:00:00+00:00')
        self.assertEqual(transport['end_date'], '2019-03-20T10:15:00+00:00')
        self.assertAlmostEqual(transport['origin_latitude'], 35.6812)
        self.assertAlmostEqual(transport['destination_longitude'], 135.7581)

        note = metadata['notes'][0]
        self.assertEqual(note['name'], 'Packing')
        self.assertEqual(note['date'], '2019-03-19')

        checklist = metadata['checklists'][0]
        self.assertEqual(checklist['name'], 'Before departure')
        self.assertEqual(checklist['items'][0]['name'], 'Passport')
        self.assertTrue(checklist['items'][0]['is_checked'])

    def test_import_round_trips_exported_collection_metadata(self):
        metadata = self._export_metadata()
        response = self._import_zip(metadata)

        self.assertEqual(response.status_code, 201)
        imported = Collection.objects.get(id=response.json()['id'])
        self.assertEqual(imported.name, 'Japan 2019 (1)')
        self.assertEqual(imported.start_date, date(2019, 3, 20))
        self.assertEqual(imported.end_date, date(2019, 3, 28))

        lodging = Lodging.objects.get(collection=imported)
        self.assertEqual(lodging.name, 'Kyoto Ryokan')
        self.assertEqual(lodging.check_in, datetime(2019, 3, 20, 15, 0, tzinfo=timezone.utc))
        self.assertEqual(lodging.check_out, datetime(2019, 3, 24, 10, 0, tzinfo=timezone.utc))
        lat, lon = point_to_lat_lon(lodging.coordinates)
        self.assertAlmostEqual(lat, 35.0116)
        self.assertAlmostEqual(lon, 135.7681)

        transport = Transportation.objects.get(collection=imported)
        self.assertEqual(transport.type, 'train')
        self.assertEqual(transport.date, datetime(2019, 3, 20, 8, 0, tzinfo=timezone.utc))
        origin_lat, origin_lon = point_to_lat_lon(transport.origin)
        self.assertAlmostEqual(origin_lat, 35.6812)
        self.assertAlmostEqual(origin_lon, 139.7671)

        note = Note.objects.get(collection=imported)
        self.assertEqual(note.name, 'Packing')
        self.assertEqual(note.date, date(2019, 3, 19))

        checklist = Checklist.objects.get(collection=imported)
        self.assertEqual(checklist.checklistitem_set.get().name, 'Passport')
        self.assertTrue(checklist.checklistitem_set.get().is_checked)

        # Existing location should be linked rather than duplicated
        self.assertEqual(imported.locations.count(), 1)
        self.assertEqual(imported.locations.get().id, self.location.id)

    def test_import_accepts_legacy_field_names(self):
        metadata = {
            'collection': {
                'name': 'Legacy Trip',
                'start_date': '2018-07-01',
                'end_date': '2018-07-10',
            },
            'locations': [],
            'transportation': [
                {
                    'transportation_type': 'plane',
                    'name': 'Flight home',
                    'notes': 'Evening departure',
                    'date': '2018-07-10T18:00:00+00:00',
                }
            ],
            'notes': [
                {'title': 'Old note', 'content': 'hello'},
            ],
            'checklists': [
                {
                    'name': 'Old list',
                    'items': [{'name': 'Sunscreen', 'completed': True}],
                }
            ],
            'lodging': [
                {
                    'lodging_type': 'hostel',
                    'name': 'Downtown Hostel',
                    'notes': 'Bunk room',
                    'check_in': '2018-07-01T14:00:00Z',
                    'check_out': '2018-07-05T11:00:00Z',
                    'latitude': 40.7128,
                    'longitude': -74.006,
                }
            ],
        }

        response = self._import_zip(metadata)
        self.assertEqual(response.status_code, 201)
        imported = Collection.objects.get(id=response.json()['id'])
        self.assertEqual(imported.start_date, date(2018, 7, 1))
        self.assertEqual(imported.end_date, date(2018, 7, 10))

        lodging = Lodging.objects.get(collection=imported)
        self.assertEqual(lodging.type, 'hostel')
        self.assertEqual(lodging.description, 'Bunk room')
        self.assertEqual(lodging.check_in, datetime(2018, 7, 1, 14, 0, tzinfo=timezone.utc))
        lat, lon = point_to_lat_lon(lodging.coordinates)
        self.assertAlmostEqual(lat, 40.7128)
        self.assertAlmostEqual(lon, -74.006)

        transport = Transportation.objects.get(collection=imported)
        self.assertEqual(transport.type, 'plane')
        self.assertEqual(transport.description, 'Evening departure')

        self.assertEqual(Note.objects.get(collection=imported).name, 'Old note')
        self.assertTrue(Checklist.objects.get(collection=imported).checklistitem_set.get().is_checked)
