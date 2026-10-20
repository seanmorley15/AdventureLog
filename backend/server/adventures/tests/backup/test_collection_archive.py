"""A collection as a file: what it carries, what it leaves out, and how it is added back."""

import io
import json
import shutil
import tempfile
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import (
    Activity, Category, Collection, CollectionComment, CollectionGuestLink, CollectionInvite,
    CollectionItineraryDay, CollectionItineraryItem, CollectionMember, ContentAttachment,
    ContentImage, Location, Lodging, Note, Trail, Transportation,
)
from adventures.tests.factories import build_rich_account
from adventures.utils.collection_type import BACKUP_SCHEMA
from users.models import CustomUser
from worldtravel.models import VisitedCity, VisitedRegion


class CollectionArchiveTests(APITestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root, ADVENTURELOG_RELEASE_VERSION='test')
        override.enable()
        self.addCleanup(override.disable)

        self.owner = CustomUser.objects.create_user(
            username='arc-owner', email='arc-owner@example.com', password='testpassword123'
        )
        self.friend = CustomUser.objects.create_user(
            username='arc-friend', email='arc-friend@example.com', password='testpassword123', public_profile=True
        )
        self.importer = CustomUser.objects.create_user(
            username='arc-importer', email='arc-importer@example.com', password='testpassword123'
        )
        self.objects = build_rich_account(self.owner, self.friend)
        self.trip = self.objects['trip']

    def as_user(self, user):
        self.client.force_authenticate(user=user)

    def export_bytes(self):
        self.as_user(self.owner)
        response = self.client.get(f'/api/collections/{self.trip.id}/export/')
        self.assertEqual(response.status_code, 200)
        return response.content

    def export_data(self):
        with zipfile.ZipFile(io.BytesIO(self.export_bytes())) as archive:
            return json.loads(archive.read('data.json'))

    def upload(self, content, user=None, **fields):
        self.as_user(user or self.importer)
        file = SimpleUploadedFile('collection.zip', content, content_type='application/zip')
        return self.client.post('/api/collections/import/', {'file': file, **fields}, format='multipart')

    # ---- what the file carries

    def test_the_file_is_a_collection_archive_without_personal_or_access_details(self):
        data = self.export_data()

        self.assertEqual(data['archive_kind'], 'collection')
        self.assertEqual(data['backup_schema'], BACKUP_SCHEMA)
        for key in ('user_email', 'user_username', 'export_date', 'visited_cities', 'visited_regions'):
            self.assertNotIn(key, data) if key in ('user_email', 'user_username', 'export_date') else self.assertEqual(data[key], [])
        collection = data['collections'][0]
        self.assertEqual((collection['members'], collection['guest_links'], collection['shared_with_user_ids']), ([], [], []))
        self.assertTrue(all(c['author_guest_token'] is None for c in collection['comments']))

    def test_only_this_collections_records_are_in_the_file(self):
        data = self.export_data()

        self.assertEqual(sorted(l['name'] for l in data['locations']), ['Café du Lac', 'Refuge du Goûter'])
        self.assertEqual([n['name'] for n in data['notes']], ['Packing'])
        self.assertEqual(len(data['collections']), 1)

    def test_only_the_owner_can_download_it(self):
        self.as_user(self.friend)
        response = self.client.get(f'/api/collections/{self.trip.id}/export/')
        self.assertEqual(response.status_code, 404)

    def test_an_archived_collection_can_still_be_downloaded_by_its_owner(self):
        Collection.objects.filter(pk=self.trip.pk).update(is_archived=True)

        data = self.export_data()

        self.assertEqual(data['collections'][0]['name'], 'Alps')
        self.assertTrue(data['collections'][0]['is_archived'])

    # ---- adding it to another account

    def test_importing_into_another_account_brings_back_everything_in_the_collection(self):
        response = self.upload(self.export_bytes())

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        imported = Collection.objects.get(id=body['id'])
        self.assertEqual(imported.user, self.importer)
        self.assertEqual(
            (imported.name, imported.type, str(imported.start_date), str(imported.end_date), imported.timezone),
            ('Alps', 'trip', '2026-06-01', '2026-06-05', 'Europe/Paris'),
        )
        self.assertEqual(
            (imported.description, imported.link, imported.visibility, imported.comment_access),
            ('Summer in the Alps', 'https://example.com/alps', 'unlisted', 'signed_in'),
        )
        self.assertEqual(imported.story_groups, {'costs': True})
        self.assertNotEqual(imported.share_secret, self.trip.share_secret)
        self.assertEqual(body['import_summary']['locations'], 2)

        hut = Location.objects.get(user=self.importer, name='Refuge du Goûter')
        self.assertEqual((hut.tags, hut.rating, str(hut.price.amount), hut.price.currency.code),
                         (['hut', 'alpine'], 4.5, '120.00', 'EUR'))
        self.assertEqual((hut.city_id, hut.region_id, hut.country.country_code), ('FR-ARA-1', 'FR-ARA', 'FR'))
        self.assertEqual((hut.category.name, hut.category.display_name, hut.category.icon), ('food', 'Food & Drink', '🍜'))
        self.assertEqual(sorted(l.name for l in imported.locations.all()), ['Café du Lac', 'Refuge du Goûter'])

        self.assertEqual(hut.visits.count(), 2)
        visit = hut.visits.get(notes='Clear skies')
        self.assertEqual(visit.timezone, 'Europe/Paris')
        activity = Activity.objects.get(visit=visit)
        self.assertEqual((activity.name, activity.distance, activity.trail.name), ('Ascent', 7200.5, 'Tête Rousse route'))
        self.assertTrue(activity.gpx_file)
        self.assertEqual(ContentImage.objects.filter(object_id=activity.id).count(), 1)
        trail = Trail.objects.get(location=hut)
        self.assertEqual((trail.wanderer_id, trail.wanderer_author_username), ('w-1', 'ana'))
        self.assertEqual(ContentImage.objects.filter(object_id=trail.id).count(), 1)

        self.assertEqual(ContentImage.objects.filter(object_id=hut.id).count(), 3)
        self.assertEqual(imported.primary_image.object_id, hut.id)
        self.assertEqual(ContentAttachment.objects.filter(object_id=hut.id).count(), 1)
        self.assertEqual(ContentImage.objects.filter(user=self.importer).count(), 12)

    def test_transport_notes_checklists_and_lodging_come_back_with_their_photos(self):
        imported = Collection.objects.get(id=self.upload(self.export_bytes()).json()['id'])

        train = Transportation.objects.get(collection=imported)
        self.assertEqual((train.start_code, train.end_code, train.price.currency.code), ('PAR', 'NCY', 'EUR'))
        self.assertEqual(ContentImage.objects.filter(object_id=train.id).count(), 1)
        self.assertEqual(ContentAttachment.objects.filter(object_id=train.id).count(), 1)
        inn = Lodging.objects.get(collection=imported)
        self.assertEqual((str(inn.price.amount), inn.reservation_number), ('0.00', 'CH-77'))
        note = Note.objects.get(collection=imported)
        self.assertTrue(note.is_private)
        self.assertEqual(ContentImage.objects.filter(object_id=note.id).count(), 1)
        checklist = imported.checklist_set.get()
        self.assertEqual(sorted((i.name, i.is_private) for i in checklist.checklistitem_set.all()),
                         [('Gift', True), ('Passport', False)])
        self.assertFalse(Note.objects.filter(user=self.importer, name='Loose note').exists())

    def test_the_day_plan_comes_back(self):
        imported = Collection.objects.get(id=self.upload(self.export_bytes()).json()['id'])

        days = list(CollectionItineraryDay.objects.filter(collection=imported).order_by('index'))
        self.assertEqual([(d.index, d.name) for d in days], [(i, f'Day {i}') for i in range(1, 6)])
        self.assertEqual(CollectionItineraryItem.objects.filter(collection=imported).count(), 6)
        stay = CollectionItineraryItem.objects.get(collection=imported, span_end_index=4)
        self.assertEqual(stay.day.index, 2)
        hut_row = CollectionItineraryItem.objects.get(collection=imported, is_optional=True)
        self.assertEqual(hut_row.logged_visit.notes, 'Clear skies')
        self.assertEqual(CollectionItineraryItem.objects.filter(collection=imported, is_global=True).count(), 2)

        self.assertEqual(Trail.objects.filter(collection=imported).count(), 1)
        self.assertEqual(Trail.objects.get(day__collection=imported).span_end_index, 4)
        run = Activity.objects.get(day__collection=imported)
        self.assertEqual((run.external_service_id, run.start_point is not None), ('strava-7', True))

    def test_comments_come_back_without_anyone_elses_account(self):
        imported = Collection.objects.get(id=self.upload(self.export_bytes()).json()['id'])

        comments = {c.body: c for c in CollectionComment.objects.filter(collection=imported)}
        self.assertEqual(set(comments), {'Plan looks good', 'Agreed', 'Lovely story', 'Book the hut early'})
        self.assertTrue(all(c.author_user is None for c in comments.values()))
        self.assertEqual(comments['Agreed'].parent, comments['Plan looks good'])
        self.assertEqual(comments['Agreed'].author_name, 'Friend')
        self.assertTrue(comments['Lovely story'].is_story)
        self.assertIsNone(comments['Lovely story'].author_guest)
        self.assertEqual(comments['Book the hut early'].placement.collection_id, imported.id)

    def test_no_sharing_is_created_and_world_visits_are_not_touched(self):
        imported = Collection.objects.get(id=self.upload(self.export_bytes()).json()['id'])

        self.assertFalse(CollectionInvite.objects.filter(collection=imported).exists())
        self.assertFalse(CollectionMember.objects.filter(collection=imported).exists())
        self.assertFalse(CollectionGuestLink.objects.filter(collection=imported).exists())
        self.assertFalse(VisitedCity.objects.filter(user=self.importer).exists())
        self.assertFalse(VisitedRegion.objects.filter(user=self.importer).exists())

    def test_importing_does_not_change_the_original(self):
        before = (Location.objects.filter(user=self.owner).count(), ContentImage.objects.filter(user=self.owner).count())

        self.upload(self.export_bytes())

        self.assertEqual(before, (Location.objects.filter(user=self.owner).count(),
                                  ContentImage.objects.filter(user=self.owner).count()))

    def test_a_second_import_into_the_same_account_is_renamed(self):
        first = self.upload(self.export_bytes()).json()['name']
        second = self.upload(self.export_bytes()).json()['name']
        third = self.upload(self.export_bytes()).json()['name']

        self.assertEqual((first, second, third), ('Alps', 'Alps (1)', 'Alps (2)'))

    # ---- places the account already has

    def test_importing_into_the_owners_account_links_the_places_they_already_have(self):
        before_locations = Location.objects.filter(user=self.owner).count()
        before_images = ContentImage.objects.filter(user=self.owner).count()

        response = self.upload(self.export_bytes(), user=self.owner)

        self.assertEqual(response.status_code, 201, response.content)
        imported = Collection.objects.get(id=response.json()['id'])
        self.assertEqual(Location.objects.filter(user=self.owner).count(), before_locations)
        self.assertEqual(set(imported.locations.all()), {self.objects['hut'], self.objects['cafe']})
        self.assertEqual(response.json()['import_summary']['locations_linked'], 2)
        # What they already had is not copied again: no second set of visits or photos for the places.
        self.assertEqual(self.objects['hut'].visits.count(), 2)
        self.assertEqual(ContentImage.objects.filter(object_id=self.objects['hut'].id).count(), 3)
        # Everything else in the collection is new.
        self.assertEqual(ContentImage.objects.filter(user=self.owner).count(), before_images + 6)
        self.assertEqual(Transportation.objects.filter(collection=imported).count(), 1)

    def test_a_linked_place_still_gets_its_placements_in_the_new_plan(self):
        imported = Collection.objects.get(id=self.upload(self.export_bytes(), user=self.owner).json()['id'])

        placed = CollectionItineraryItem.objects.filter(collection=imported, object_id=self.objects['hut'].id)
        self.assertEqual(placed.count(), 1)
        self.assertIsNone(placed.get().logged_visit)

    def test_create_makes_new_copies_even_when_the_account_has_the_places(self):
        before = Location.objects.filter(user=self.owner, name='Refuge du Goûter').count()

        response = self.upload(self.export_bytes(), user=self.owner, existing_locations='create')

        self.assertEqual(response.status_code, 201, response.content)
        imported = Collection.objects.get(id=response.json()['id'])
        self.assertEqual(Location.objects.filter(user=self.owner, name='Refuge du Goûter').count(), before + 1)
        new_hut = imported.locations.get(name='Refuge du Goûter')
        self.assertNotEqual(new_hut.id, self.objects['hut'].id)
        self.assertEqual(new_hut.visits.count(), 2)
        self.assertNotIn('locations_linked', response.json()['import_summary'])

    def test_an_unknown_option_value_is_refused_before_anything_is_created(self):
        before = Collection.objects.count()

        response = self.upload(self.export_bytes(), existing_locations='merge')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Collection.objects.count(), before)

    # ---- files that are not for this endpoint

    def test_a_full_backup_is_refused_by_collection_import(self):
        self.as_user(self.owner)
        backup = self.client.get('/api/backup/export/').content

        response = self.upload(backup, user=self.owner)

        self.assertEqual(response.status_code, 400)
        self.assertIn('full backup', response.json()['error'])

    def test_a_collection_file_is_refused_by_full_restore_and_nothing_is_erased(self):
        self.as_user(self.owner)
        file = SimpleUploadedFile('collection.zip', self.export_bytes(), content_type='application/zip')

        response = self.client.post('/api/backup/import/', {'file': file, 'confirm': 'yes'}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('single collection', response.json()['error'])
        self.assertTrue(Location.objects.filter(pk=self.objects['hut'].pk).exists())
        self.assertEqual(Collection.objects.filter(user=self.owner).count(), 2)

    def test_a_file_from_a_newer_server_is_refused(self):
        data = self.export_data()
        data['backup_schema'] = BACKUP_SCHEMA + 1
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('data.json', json.dumps(data))

        response = self.upload(buffer.getvalue())

        self.assertEqual(response.status_code, 400)
        self.assertIn('newer schema', response.json()['error'])

    def test_a_zip_with_no_collection_data_is_refused(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('hello.txt', 'hi')

        response = self.upload(buffer.getvalue())

        self.assertEqual(response.status_code, 400)

    def test_a_failed_import_leaves_nothing_behind(self):
        data = self.export_data()
        data['locations'][0]['name'] = None  # a required field: the restore fails part-way
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('data.json', json.dumps(data))
        before = (Collection.objects.count(), Location.objects.count())

        response = self.upload(buffer.getvalue())

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'An internal error occurred during import')
        self.assertEqual(before, (Collection.objects.count(), Location.objects.count()))


class LegacyCollectionFileTests(APITestCase):
    """The format the app wrote before collection files carried the whole collection."""

    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.user = CustomUser.objects.create_user(
            username='legacy-user', email='legacy-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

    def legacy_zip(self, **overrides):
        from adventures.tests.factories import PNG

        metadata = {
            'version': 'old',
            'backup_schema': 3,
            'collection': {'id': 'x', 'name': 'Old trip', 'start_date': '2020-05-01', 'end_date': '2020-05-03',
                           'type': 'trip', 'timezone': 'UTC', 'is_public': True, 'day_count': 3},
            'locations': [{
                'id': 'l1', 'name': 'Old place', 'location': 'Somewhere', 'tags': ['a'], 'rating': 3,
                'latitude': 10.0, 'longitude': 20.0, 'category': 'Sights',
                'city': 'Paris', 'region': 'Île-de-France', 'country': 'France',
                'images': ['img_0'], 'attachments': ['att_0'],
            }],
            'images': [{'export_id': 'img_0', 'id': 'i1', 'name': 'pic.webp', 'is_primary': True}],
            'attachments': [{'export_id': 'att_0', 'id': 'a1', 'name': 'ticket.txt'}],
            'transportation': [], 'notes': [], 'checklists': [], 'lodging': [],
            **overrides,
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('metadata.json', json.dumps(metadata))
            archive.writestr('images/img_0-pic.webp', PNG)
            archive.writestr('attachments/ticket.txt', b'ticket')
        return buffer.getvalue()

    def upload(self, content, **fields):
        file = SimpleUploadedFile('old.zip', content, content_type='application/zip')
        return self.client.post('/api/collections/import/', {'file': file, **fields}, format='multipart')

    def test_an_old_file_still_imports_with_its_photos_attachments_and_cover(self):
        response = self.upload(self.legacy_zip())

        self.assertEqual(response.status_code, 201, response.content)
        imported = Collection.objects.get(id=response.json()['id'])
        place = imported.locations.get()
        self.assertEqual((place.name, place.category.name, place.category.display_name), ('Old place', 'Sights', 'Sights'))
        self.assertIsNone(place.city)  # the old format named these but never restored them
        self.assertEqual(ContentImage.objects.filter(object_id=place.id).count(), 1)
        self.assertEqual(imported.primary_image.object_id, place.id)
        self.assertEqual(ContentAttachment.objects.get(object_id=place.id).name, 'ticket.txt')
        self.assertEqual(imported.visibility, 'public')

    def test_an_old_trip_gets_its_day_plan_built_from_the_recorded_day_count(self):
        imported = Collection.objects.get(id=self.upload(self.legacy_zip()).json()['id'])

        self.assertEqual(CollectionItineraryDay.objects.filter(collection=imported).count(), 3)

    def test_an_old_file_can_link_or_create_places_like_a_new_one(self):
        Location.objects.create(user=self.user, name='Old place', location='Somewhere')
        from core.geo import make_point

        existing = Location.objects.get(user=self.user, name='Old place')
        existing.coordinates = make_point(20.0, 10.0)
        existing.save(_skip_geocode=True)

        linked = Collection.objects.get(id=self.upload(self.legacy_zip()).json()['id'])
        created = Collection.objects.get(id=self.upload(self.legacy_zip(), existing_locations='create').json()['id'])

        self.assertEqual(list(linked.locations.all()), [existing])
        self.assertNotEqual(created.locations.get().id, existing.id)

    def test_a_category_the_account_already_has_is_reused(self):
        Category.objects.create(user=self.user, name='Sights', display_name='My sights', icon='⭐')

        self.upload(self.legacy_zip(), existing_locations='create')

        self.assertEqual(Category.objects.filter(user=self.user, name='Sights').count(), 1)
        self.assertEqual(Category.objects.get(user=self.user, name='Sights').display_name, 'My sights')

    def test_an_old_file_from_a_newer_server_is_refused(self):
        response = self.upload(self.legacy_zip(backup_schema=BACKUP_SCHEMA + 1))

        self.assertEqual(response.status_code, 400)
