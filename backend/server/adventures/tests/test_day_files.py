"""Phase 4: day-owned trails, activities, and photos."""

import base64
import io
import json
import zipfile
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import (
    Activity,
    Collection,
    CollectionItineraryDay,
    CollectionItineraryItem,
    ContentImage,
    Location,
    Trail,
    Visit,
)
from adventures.utils.collection_type import BACKUP_SCHEMA
from users.models import CustomUser

GPX = b"""<?xml version="1.0"?>
<gpx version="1.1"><trk><trkseg>
<trkpt lat="44.0" lon="-71.0"><ele>100</ele></trkpt>
<trkpt lat="44.1" lon="-71.1"><ele>140</ele></trkpt>
</trkseg></trk></gpx>
"""

PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


@override_settings(DEBUG=True)
class DayFileTests(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='day-file-owner', email='day-file-owner@example.com', password='testpassword123'
        )
        self.member = CustomUser.objects.create_user(
            username='day-file-member', email='day-file-member@example.com', password='testpassword123'
        )
        self.stranger = CustomUser.objects.create_user(
            username='day-file-stranger', email='day-file-stranger@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.owner)
        self.trip = Collection.objects.create(
            user=self.owner,
            name='Ridge',
            type='trip',
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
            is_public=True,
        )
        self.trip.shared_with.add(self.member)
        for index in range(1, 6):
            CollectionItineraryDay.objects.create(
                collection=self.trip,
                index=index,
                date=date(2026, 6, index),
            )
        self.day3 = CollectionItineraryDay.objects.get(collection=self.trip, index=3)
        self.shelter = Location.objects.create(user=self.owner, name='Shelter')
        self.shelter.collections.add(self.trip)
        self.shelter_row = CollectionItineraryItem.objects.create(
            collection=self.trip,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.shelter.id,
            day=self.day3,
            date=self.day3.date,
            order=0,
        )
        self.place_visit = Visit.objects.create(
            location=self.shelter,
            start_date='2019-08-01T00:00:00Z',
            end_date='2019-08-01T00:00:00Z',
        )
        self.place_gpx = 'activities/place-track.gpx'
        self._write_media(self.place_gpx, b'PLACE_GPX')
        self.place_activity = Activity.objects.create(
            user=self.owner,
            visit=self.place_visit,
            name='Old hike',
            gpx_file=self.place_gpx,
        )

    def _write_media(self, relative, content):
        path = Path(settings.MEDIA_ROOT) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def _body(self, response):
        if getattr(response, 'streaming', False):
            return b''.join(response.streaming_content)
        return response.content

    def test_day_gpx_and_trail_link_create_no_location_or_visit(self):
        locations = Location.objects.count()
        visits = Visit.objects.count()
        trail = self.client.post(
            '/api/trails/',
            {'name': 'Appalachian Trail', 'link': 'https://example.com/at', 'day': str(self.day3.id), 'span_end_index': 5},
            format='json',
        )
        self.assertEqual(trail.status_code, 201, trail.content)
        activity = self.client.post(
            '/api/activities/',
            {
                'name': 'Day 3 hike',
                'sport_type': 'Hike',
                'day': str(self.day3.id),
                'trail': trail.json()['id'],
                'gpx_file': SimpleUploadedFile('hike.gpx', GPX, content_type='application/gpx+xml'),
            },
            format='multipart',
        )
        self.assertEqual(activity.status_code, 201, activity.content)
        self.assertIsNone(activity.json()['visit'])
        self.assertIsNone(trail.json()['location'])
        self.assertNotIn('gpx_file', trail.json())
        self.assertEqual(activity.json()['geojson']['features'][0]['geometry']['type'], 'LineString')
        self.assertEqual(Location.objects.count(), locations)
        self.assertEqual(Visit.objects.count(), visits)
        stored = Activity.objects.get(pk=activity.json()['id'])
        self.assertEqual(stored.user_id, self.owner.id)
        self.assertEqual(stored.day_id, self.day3.id)

        detail = self.client.get(f'/api/collections/{self.trip.id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.json()['day_activities']), 1)
        self.assertEqual(len(detail.json()['day_trails']), 1)
        self.assertTrue(detail.json()['day_activities'][0]['geojson']['features'])

    def test_anonymous_day_gpx_is_404_and_a_member_can_open_it(self):
        self._write_media('activities/day-track.gpx', b'DAY_GPX')
        activity = Activity.objects.create(
            user=self.owner,
            day=self.day3,
            name='Ridge walk',
            gpx_file='activities/day-track.gpx',
        )
        self.client.logout()
        anonymous = self.client.get(f'/media/{activity.gpx_file.name}')
        self.assertEqual(anonymous.status_code, 404)

        self.client.force_login(self.stranger)
        stranger = self.client.get(f'/media/{activity.gpx_file.name}')
        self.assertEqual(stranger.status_code, 404)

        self.client.force_login(self.member)
        member = self.client.get(f'/media/{activity.gpx_file.name}')
        self.assertEqual(member.status_code, 200)
        self.assertEqual(self._body(member), b'DAY_GPX')

    def test_public_location_gpx_stays_readable(self):
        public = Location.objects.create(user=self.owner, name='Lookout', is_public=True)
        visit = Visit.objects.create(location=public)
        self._write_media('activities/public-track.gpx', b'PUBLIC_GPX')
        Activity.objects.create(user=self.owner, visit=visit, name='Public', gpx_file='activities/public-track.gpx')
        self.client.logout()
        response = self.client.get('/media/activities/public-track.gpx')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._body(response), b'PUBLIC_GPX')

    def test_log_visit_copies_gpx_onto_the_only_stop_and_leaves_the_day_activity(self):
        self._write_media('activities/copy-me.gpx', GPX)
        activity = Activity.objects.create(
            user=self.owner, day=self.day3, name='Day 3 hike', sport_type='Hike', gpx_file='activities/copy-me.gpx'
        )
        response = self.client.post(f'/api/activities/{activity.id}/log-visited/', {}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        activity.refresh_from_db()
        self.assertIsNone(activity.visit_id)
        self.assertEqual(activity.day_id, self.day3.id)
        copy = activity.promoted_activity
        self.assertIsNotNone(copy)
        self.assertEqual(copy.visit.location_id, self.shelter.id)
        self.assertTrue(copy.gpx_file)
        self.assertNotEqual(copy.gpx_file.name, activity.gpx_file.name)
        self.assertEqual(Visit.objects.filter(location=self.shelter).count(), 2)
        self.shelter_row.refresh_from_db()
        self.assertEqual(self.shelter_row.logged_visit_id, copy.visit_id)

        again = self.client.post(f'/api/activities/{activity.id}/log-visited/', {}, format='json')
        self.assertEqual(again.status_code, 200, again.content)
        self.assertEqual(Activity.objects.filter(visit__location=self.shelter).count(), 2)

    def test_several_stops_ask_which_one_and_location_log_does_not_move_the_day_file(self):
        town = Location.objects.create(user=self.owner, name='Town')
        town.collections.add(self.trip)
        town_row = CollectionItineraryItem.objects.create(
            collection=self.trip,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=town.id,
            day=self.day3,
            date=self.day3.date,
            order=1,
        )
        activity = Activity.objects.create(user=self.owner, day=self.day3, name='Linkup')
        asked = self.client.post(f'/api/activities/{activity.id}/log-visited/', {}, format='json')
        self.assertEqual(asked.status_code, 400)
        self.assertEqual(asked.json()['code'], 'stop_required')
        self.assertEqual(len(asked.json()['stops']), 2)

        chosen = self.client.post(
            f'/api/activities/{activity.id}/log-visited/',
            {'placement': str(town_row.id)},
            format='json',
        )
        self.assertEqual(chosen.status_code, 201, chosen.content)
        activity.refresh_from_db()
        self.assertEqual(activity.promoted_activity.visit.location_id, town.id)
        self.assertIsNone(activity.visit_id)

        logged = self.client.post(f'/api/itineraries/{self.shelter_row.id}/log-visited/', {}, format='json')
        self.assertEqual(logged.status_code, 201, logged.content)
        activity.refresh_from_db()
        self.assertEqual(activity.day_id, self.day3.id)
        self.assertEqual(Activity.objects.filter(day=self.day3).count(), 1)

    def test_log_day_includes_the_day_activity(self):
        Activity.objects.create(user=self.owner, day=self.day3, name='Included')
        response = self.client.post(
            '/api/itineraries/log-day/',
            {'collection': str(self.trip.id), 'day': str(self.day3.id)},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        activity = Activity.objects.get(day=self.day3)
        self.assertIsNotNone(activity.promoted_activity_id)
        self.assertEqual(activity.promoted_activity.visit.location_id, self.shelter.id)

    def test_delete_day_moves_files_to_ideas_or_another_day(self):
        activity = Activity.objects.create(user=self.owner, day=self.day3, name='Move me')
        Trail.objects.create(user=self.owner, day=self.day3, name='AT', link='https://example.com/at')
        refused = self.client.post(
            '/api/itineraries/days/delete/',
            {'collection': str(self.trip.id), 'day': str(self.day3.id)},
            format='json',
        )
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()['code'], 'destination_required')

        moved = self.client.post(
            '/api/itineraries/days/delete/',
            {'collection': str(self.trip.id), 'day': str(self.day3.id), 'destination': 'ideas'},
            format='json',
        )
        self.assertEqual(moved.status_code, 200, moved.content)
        activity.refresh_from_db()
        self.assertIsNone(activity.day_id)
        self.assertEqual(activity.collection_id, self.trip.id)
        trail = Trail.objects.get(name='AT')
        self.assertIsNone(trail.day_id)
        self.assertEqual(trail.collection_id, self.trip.id)
        self.assertIsNone(trail.location_id)

    def test_delete_collection_removes_day_files_and_leaves_the_location(self):
        self._write_media('activities/copy-me.gpx', GPX)
        activity = Activity.objects.create(
            user=self.owner, day=self.day3, name='Day 3 hike', gpx_file='activities/copy-me.gpx'
        )
        self.client.post(f'/api/activities/{activity.id}/log-visited/', {}, format='json')
        copy_id = Activity.objects.get(pk=activity.id).promoted_activity_id
        self.trip.delete()
        self.assertTrue(Location.objects.filter(pk=self.shelter.id).exists())
        self.assertTrue(Activity.objects.filter(pk=self.place_activity.id).exists())
        self.assertTrue(Activity.objects.filter(pk=copy_id).exists())
        self.assertFalse(Activity.objects.filter(pk=activity.id).exists())

    def test_day_photo_can_be_the_cover(self):
        image = ContentImage.objects.create(
            user=self.owner,
            image=SimpleUploadedFile('cover.png', PNG, content_type='image/png'),
            content_type=ContentType.objects.get_for_model(CollectionItineraryDay),
            object_id=self.day3.id,
        )
        response = self.client.patch(
            f'/api/collections/{self.trip.id}/',
            {'primary_image_id': str(image.id)},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.primary_image_id, image.id)

    def test_schema_4_round_trip_and_schema_3_without_keys(self):
        Trail.objects.create(
            user=self.owner, day=self.day3, name='AT', link='https://example.com/at', span_end_index=4
        )
        Activity.objects.create(user=self.owner, day=self.day3, name='Day 3 hike', sport_type='Hike')
        exported = self.client.get('/api/backup/export/')
        self.assertEqual(exported.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(exported.content)) as zipf:
            data = json.loads(zipf.read('data.json'))
        self.assertEqual(data['backup_schema'], BACKUP_SCHEMA)
        self.assertEqual(len(data['day_trails']), 1)
        self.assertEqual(len(data['day_activities']), 1)

        self.trip.delete()
        restored = self.client.post(
            '/api/backup/import/',
            {'file': SimpleUploadedFile('backup.zip', exported.content, content_type='application/zip'), 'confirm': 'yes'},
            format='multipart',
        )
        self.assertEqual(restored.status_code, 200, restored.content)
        trip = Collection.objects.get(user=self.owner, name='Ridge')
        self.assertEqual(Trail.objects.filter(day__collection=trip).count(), 1)
        self.assertEqual(Activity.objects.filter(day__collection=trip, visit__isnull=True).count(), 1)

        payload = {
            'backup_schema': 3,
            'version': 'v0.13.0',
            'collections': [
                {'export_id': 0, 'name': 'Older', 'type': 'trip', 'start_date': '2026-07-01', 'end_date': '2026-07-02', 'timezone': 'UTC'},
            ],
            'itinerary_days': [
                {'collection_export_id': 0, 'index': 1, 'date': '2026-07-01', 'name': None, 'description': None},
                {'collection_export_id': 0, 'index': 2, 'date': '2026-07-02', 'name': None, 'description': None},
            ],
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zipf:
            zipf.writestr('data.json', json.dumps(payload))
        older = self.client.post(
            '/api/backup/import/',
            {'file': SimpleUploadedFile('old.zip', buffer.getvalue(), content_type='application/zip'), 'confirm': 'yes'},
            format='multipart',
        )
        self.assertEqual(older.status_code, 200, older.content)
        self.assertTrue(Collection.objects.filter(user=self.owner, name='Older').exists())

    def test_collaborator_day_activity_belongs_to_the_collection_owner(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            '/api/activities/',
            {'name': 'Shared hike', 'sport_type': 'Hike', 'day': str(self.day3.id)},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        stored = Activity.objects.get(pk=response.json()['id'])
        self.assertEqual(stored.user_id, self.owner.id)
        self.assertIsNone(stored.visit_id)
