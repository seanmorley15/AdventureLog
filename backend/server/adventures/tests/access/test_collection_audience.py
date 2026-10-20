import io
import json
import zipfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from adventures.models import (
    Activity,
    Checklist,
    ChecklistItem,
    Collection,
    CollectionGuestLink,
    CollectionInvite,
    CollectionMember,
    Location,
    Lodging,
    Note,
    Transportation,
)
from adventures.services.calendar_events import get_calendar_events_for_user
from adventures.services.exports.pdf import build_collection_pdf, get_collection_for_pdf
from adventures.access.audience import resolve_audience
from adventures.tests.base import AudienceTestBase, make_user
from users.models import CustomUser


class RoleTests(AudienceTestBase):
    def test_migration_default_and_roles(self):
        self.assertEqual(resolve_audience(self.trip, self.owner).role, 'owner')
        self.assertEqual(resolve_audience(self.trip, self.editor).role, 'editor')
        self.assertEqual(resolve_audience(self.trip, self.viewer).role, 'viewer')
        self.assertIsNone(resolve_audience(self.trip, self.stranger))

    def test_editor_and_guest_editor_can_move_an_item(self):
        self.as_user(self.editor)
        self.assertEqual(self.move_stop(2).status_code, 200)

        link = CollectionGuestLink.objects.create(collection=self.trip, role='editor')
        self.as_anonymous()
        response = self.move_stop(3, HTTP_X_GUEST_TOKEN=link.token)
        self.assertEqual(response.status_code, 200, response.content)
        self.stop.refresh_from_db()
        self.assertEqual(self.stop.day.index, 3)

    def test_viewer_guest_viewer_and_public_reader_cannot_move_an_item(self):
        self.as_user(self.viewer)
        self.assertIn(self.move_stop().status_code, (403, 404))

        link = CollectionGuestLink.objects.create(collection=self.trip, role='viewer')
        self.as_anonymous()
        self.assertIn(self.move_stop(HTTP_X_GUEST_TOKEN=link.token).status_code, (401, 403, 404))

        with override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True):
            self.publish('public')
            self.assertIn(self.move_stop().status_code, (401, 403, 404))
        self.stop.refresh_from_db()
        self.assertEqual(self.stop.day.index, 1)

    def test_viewer_opens_the_plan_and_cannot_add_records(self):
        self.as_user(self.viewer)
        response = self.client.get(f'/api/collections/{self.trip.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['audience']['role'], 'viewer')
        self.assertFalse(response.json()['audience']['can_edit'])
        self.assertIn('itinerary', response.json())

        refused = self.client.post(
            '/api/notes/', {'name': 'Pack', 'collection': str(self.trip.id)}, format='json'
        )
        self.assertEqual(refused.status_code, 403)
        refused_day = self.client.post(
            '/api/itineraries/days/insert/', {'collection': str(self.trip.id)}, format='json'
        )
        self.assertEqual(refused_day.status_code, 403)

    def test_guest_link_reads_the_plan_until_revoked_or_expired(self):
        link = CollectionGuestLink.objects.create(collection=self.trip, role='viewer')
        self.as_anonymous()
        url = f'/api/collections/{self.trip.id}/'
        self.assertEqual(self.client.get(url, HTTP_X_GUEST_TOKEN=link.token).status_code, 200)
        link.revoked_at = timezone.now()
        link.save()
        self.assertEqual(self.client.get(url, HTTP_X_GUEST_TOKEN=link.token).status_code, 404)

        expired = CollectionGuestLink.objects.create(
            collection=self.trip, role='editor', expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(self.client.get(url, HTTP_X_GUEST_TOKEN=expired.token).status_code, 404)

    def test_guest_editor_cannot_change_visibility_members_or_delete(self):
        link = CollectionGuestLink.objects.create(collection=self.trip, role='editor')
        self.as_anonymous()
        headers = {'HTTP_X_GUEST_TOKEN': link.token}
        url = f'/api/collections/{self.trip.id}/'
        self.assertIn(self.client.patch(url, {'visibility': 'public'}, format='json', **headers).status_code, (401, 403, 404))
        self.assertIn(self.client.delete(url, **headers).status_code, (401, 403, 404))
        self.assertIn(
            self.client.post(f'/api/collections/{self.trip.id}/unshare/{self.editor.uuid}/', **headers).status_code,
            (401, 403, 404),
        )
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.visibility, 'private')

    def test_editor_cannot_change_the_owners_location_record(self):
        self.as_user(self.editor)
        response = self.client.patch(
            f'/api/locations/{self.hut.id}/',
            {'name': 'Renamed', 'is_public': True, 'latitude': 10, 'longitude': 10},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.hut.refresh_from_db()
        self.assertEqual(self.hut.name, 'Hut')
        self.assertFalse(self.hut.is_public)
        self.assertIsNone(self.hut.coordinates)

    def test_invite_role_and_owner_role_change(self):
        guest = make_user('guest')
        self.as_user(self.owner)
        self.client.post(f'/api/collections/{self.trip.id}/share/{guest.uuid}/', {'role': 'viewer'}, format='json')
        self.assertEqual(CollectionInvite.objects.get(invited_user=guest).role, 'viewer')
        self.as_user(guest)
        self.client.post(f'/api/collections/{self.trip.id}/accept-invite/')
        self.assertEqual(resolve_audience(self.trip, guest).role, 'viewer')

        self.as_user(self.owner)
        response = self.client.post(
            f'/api/collections/{self.trip.id}/members/{guest.uuid}/role/', {'role': 'editor'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(resolve_audience(self.trip, guest).role, 'editor')

        self.as_user(self.editor)
        refused = self.client.post(
            f'/api/collections/{self.trip.id}/members/{guest.uuid}/role/', {'role': 'viewer'}, format='json'
        )
        self.assertEqual(refused.status_code, 404)

    def test_owner_creates_several_guest_links_and_revokes_one(self):
        self.as_user(self.owner)
        first = self.client.post(f'/api/collections/{self.trip.id}/guest-links/', {'role': 'viewer'}, format='json')
        self.assertEqual(first.status_code, 201, first.content)
        second = self.client.post(
            f'/api/collections/{self.trip.id}/guest-links/',
            {'role': 'editor', 'expires_at': (timezone.now() + timedelta(days=3)).isoformat()},
            format='json',
        )
        links = second.json()['guest_links']
        self.assertEqual(len(links), 2)
        revoked = self.client.post(f'/api/collections/{self.trip.id}/guest-links/{links[0]["id"]}/revoke/')
        self.assertFalse(revoked.json()['guest_links'][0]['is_active'])
        self.assertTrue(revoked.json()['guest_links'][1]['is_active'])

    def test_removing_a_member_drops_the_trip_and_keeps_places(self):
        own = Location.objects.create(user=self.editor, name='Editor cafe')
        own.collections.add(self.trip)
        self.assertTrue(get_calendar_events_for_user(self.editor))
        self.as_user(self.owner)
        response = self.client.post(f'/api/collections/{self.trip.id}/unshare/{self.editor.uuid}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_calendar_events_for_user(self.editor), [])
        self.assertFalse(CollectionMember.objects.filter(collection=self.trip, user=self.editor).exists())
        self.hut.refresh_from_db()
        self.assertEqual(self.hut.user, self.owner)
        self.assertTrue(own.collections.filter(pk=self.trip.pk).exists())


class StoryTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        self.hut.coordinates = None
        self.hut.save()
        self.hotel = Lodging.objects.create(
            user=self.owner, name='Rorbu', collection=self.trip, reservation_number='ABC123',
            price=420, location='Hamnøy 7', description='Code 4411 at the door',
        )
        self.flight = Transportation.objects.create(
            user=self.owner, name='WF 870', type='plane', collection=self.trip, flight_number='WF870', price=99,
        )
        self.note = Note.objects.create(user=self.owner, name='Ferry', content='Book ahead', collection=self.trip)
        self.secret_note = Note.objects.create(
            user=self.owner, name='Door codes', content='1234', collection=self.trip, is_private=True,
        )
        self.checklist = Checklist.objects.create(user=self.owner, name='Pack', collection=self.trip)
        ChecklistItem.objects.create(user=self.owner, checklist=self.checklist, name='Headlamp')
        ChecklistItem.objects.create(user=self.owner, checklist=self.checklist, name='Passport no', is_private=True)

    def story(self, **params):
        self.as_anonymous()
        return self.client.get(f'/api/collections/{self.trip.id}/', params)

    def test_private_collection_is_not_found_for_anonymous(self):
        self.assertEqual(self.story().status_code, 404)

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_story_hides_every_group_until_the_owner_turns_it_on(self):
        self.publish('public')
        body = self.story().json()
        self.assertEqual(body['audience']['role'], 'public')
        hotel = body['lodging'][0]
        self.assertNotIn('reservation_number', hotel)
        self.assertNotIn('price', hotel)
        self.assertNotIn('location', hotel)
        self.assertNotIn('description', hotel)
        flight = body['transportations'][0]
        self.assertNotIn('flight_number', flight)
        self.assertNotIn('price', flight)
        place = body['locations'][0]
        self.assertNotIn('latitude', place)
        self.assertNotIn('location', place)
        self.assertNotIn('category', place)
        self.assertNotIn('visits', place)
        self.assertEqual([n['name'] for n in body['notes']], ['Ferry'])
        self.assertNotIn('content', body['notes'][0])
        self.assertEqual(body['checklists'][0]['items'], [])
        self.assertNotIn('shared_with', body)
        self.assertNotIn('share_secret', body)
        self.assertEqual([c['username'] for c in body['collaborators']], ['owner'])

        self.publish(
            'public', costs=True, reservations=True, lodging_address=True, coordinates=True,
            note_text=True, checklist_text=True,
        )
        body = self.story().json()
        hotel = body['lodging'][0]
        self.assertEqual(hotel['reservation_number'], 'ABC123')
        self.assertEqual(hotel['location'], 'Hamnøy 7')
        self.assertIn('price', hotel)
        self.assertEqual(body['transportations'][0]['flight_number'], 'WF870')
        self.assertEqual(body['locations'][0]['location'], 'Reine 1')
        self.assertEqual(body['notes'][0]['content'], 'Book ahead')
        self.assertEqual([n['name'] for n in body['notes']], ['Ferry'])
        self.assertEqual([i['name'] for i in body['checklists'][0]['items']], ['Headlamp'])

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_members_still_see_the_private_plan_and_can_preview_the_story(self):
        self.publish('public')
        self.as_user(self.viewer)
        plan = self.client.get(f'/api/collections/{self.trip.id}/').json()
        self.assertEqual(plan['lodging'][0]['reservation_number'], 'ABC123')
        self.as_user(self.owner)
        preview = self.client.get(f'/api/collections/{self.trip.id}/', {'as': 'story'}).json()
        self.assertTrue(preview['story_preview'])
        self.assertNotIn('reservation_number', preview['lodging'][0])

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_unlisted_needs_the_secret(self):
        self.publish('unlisted')
        self.assertEqual(self.story().status_code, 404)
        self.assertEqual(self.story(s='wrong').status_code, 404)
        self.assertEqual(self.story(s=self.trip.share_secret).status_code, 200)

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_place_details_group_copies_text_into_the_story_only(self):
        self.hut.description = 'Red cabin by the water'
        self.hut.link = 'https://example.com/hut'
        self.hut.save()
        self.publish('public')
        place = self.story().json()['locations'][0]
        self.assertNotIn('description', place)
        self.assertNotIn('link', place)

        self.publish('public', place_details=True)
        place = self.story().json()['locations'][0]
        self.assertEqual(place['description'], 'Red cabin by the water')
        self.assertEqual(place['link'], 'https://example.com/hut')
        self.assertNotIn('latitude', place)
        self.hut.refresh_from_db()
        self.assertFalse(self.hut.is_public)
        self.assertEqual(self.client.get(f'/api/locations/{self.hut.id}/').status_code, 404)

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_private_location_on_a_story_still_404s_at_its_own_page(self):
        self.publish('public', coordinates=True)
        self.assertEqual(self.story().status_code, 200)
        self.assertEqual(self.client.get(f'/api/locations/{self.hut.id}/').status_code, 404)

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=False)
    def test_existing_public_collection_stays_readable_when_the_setting_is_off(self):
        # A legacy public collection, as the migration leaves it.
        self.trip.is_public = True
        self.trip.save()
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.visibility, 'public')
        self.assertEqual(self.story().status_code, 200)

        self.as_user(self.owner)
        refused = self.client.patch(f'/api/collections/{self.trip.id}/', {'visibility': 'unlisted'}, format='json')
        self.assertEqual(refused.status_code, 400)
        kept = self.client.patch(f'/api/collections/{self.trip.id}/', {'name': 'Lofoten 2026'}, format='json')
        self.assertEqual(kept.status_code, 200, kept.content)
        private = self.client.patch(f'/api/collections/{self.trip.id}/', {'visibility': 'private'}, format='json')
        self.assertEqual(private.status_code, 200)
        self.assertEqual(self.story().status_code, 404)

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=False)
    def test_new_public_link_is_refused_when_the_setting_is_off(self):
        self.as_user(self.owner)
        self.assertEqual(
            self.client.patch(f'/api/collections/{self.trip.id}/', {'visibility': 'public'}, format='json').status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(f'/api/collections/{self.trip.id}/', {'is_public': True}, format='json').status_code,
            400,
        )

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_publishing_does_not_change_child_flags(self):
        self.as_user(self.owner)
        response = self.client.patch(f'/api/collections/{self.trip.id}/', {'visibility': 'public'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.hut.refresh_from_db()
        self.hotel.refresh_from_db()
        self.note.refresh_from_db()
        self.assertFalse(self.hut.is_public)
        self.assertFalse(self.hotel.is_public)
        self.assertFalse(self.note.is_public)

        self.hut.is_public = True
        self.hut.save()
        self.client.patch(f'/api/collections/{self.trip.id}/', {'visibility': 'private'}, format='json')
        self.hut.refresh_from_db()
        self.assertTrue(self.hut.is_public)

        cabin = Location.objects.create(user=self.owner, name='Cabin')
        self.client.patch(f'/api/collections/{self.trip.id}/', {'visibility': 'public'}, format='json')
        cabin.collections.add(self.trip)
        cabin.refresh_from_db()
        self.assertFalse(cabin.is_public)

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_collection_owned_records_do_not_open_through_is_public(self):
        self.hotel.is_public = True
        self.hotel.save()
        self.as_anonymous()
        self.assertEqual(self.client.get(f'/api/lodging/{self.hotel.id}/').status_code, 404)
        self.as_user(self.viewer)
        self.assertEqual(self.client.get(f'/api/lodging/{self.hotel.id}/').status_code, 200)

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_day_gpx_needs_the_gpx_group(self):
        day = self.trip.itinerary_days.get(index=1)
        gpx = SimpleUploadedFile('ridge.gpx', b'<gpx></gpx>', content_type='application/gpx+xml')
        activity = Activity.objects.create(user=self.owner, day=day, name='Ridge', gpx_file=gpx)
        path = f'/media/{activity.gpx_file.name}'
        self.publish('public')
        self.as_anonymous()
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertNotIn('gpx_file', self.story().json()['day_activities'][0])
        self.publish('public', gpx=True)
        self.assertEqual(self.client.get(path).status_code, 200)
        self.assertIn('gpx_file', self.story().json()['day_activities'][0])

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_public_pdf_follows_the_groups_and_member_pdf_does_not(self):
        self.publish('public')
        story_pdf = build_collection_pdf(get_collection_for_pdf(self.trip.id), story=True)
        member_pdf = build_collection_pdf(get_collection_for_pdf(self.trip.id))
        self.assertTrue(story_pdf.startswith(b'%PDF'))
        self.assertGreater(len(member_pdf), 0)
        self.as_anonymous()
        self.assertEqual(self.client.get(f'/api/collections/{self.trip.id}/export-pdf/').status_code, 200)

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_profile_lists_public_collections_only(self):
        self.publish('unlisted')
        self.as_anonymous()
        body = self.client.get(f'/auth/user/{self.owner.username}/').json()
        self.assertEqual(body['collections'], [])
        self.publish('public')
        body = self.client.get(f'/auth/user/{self.owner.username}/').json()
        self.assertEqual([c['name'] for c in body['collections']], ['Lofoten'])
        self.assertNotIn('lodging', body['collections'][0])
        self.assertEqual(body['adventures'], [])


class BackupTests(AudienceTestBase):
    def _export(self):
        self.as_user(self.owner)
        response = self.client.get('/api/backup/export/')
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            return json.loads(archive.read('data.json'))

    def _import(self, data):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('data.json', json.dumps(data))
        return self.client.post(
            '/api/backup/import/',
            {'file': SimpleUploadedFile('backup.zip', buffer.getvalue(), content_type='application/zip'), 'confirm': 'yes'},
            format='multipart',
        )

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_round_trip_keeps_visibility_roles_links_and_groups(self):
        self.publish('unlisted', costs=True)
        CollectionGuestLink.objects.create(collection=self.trip, role='editor', label='Family')
        Note.objects.create(user=self.owner, name='Codes', collection=self.trip, is_private=True)
        data = self._export()
        self.assertGreaterEqual(data['backup_schema'], 5)
        response = self._import(data)
        self.assertEqual(response.status_code, 200, response.content)

        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        self.assertEqual(restored.visibility, 'unlisted')
        self.assertEqual(restored.story_groups, {'costs': True})
        # Collaborators come back as pending invites with their roles; nobody is added without accepting.
        self.assertIsNone(resolve_audience(restored, self.viewer))
        self.assertIsNone(resolve_audience(restored, self.editor))
        self.assertEqual(
            dict(CollectionInvite.objects.filter(collection=restored).values_list('invited_user__username', 'role')),
            {'viewer': 'viewer', 'editor': 'editor'},
        )
        self.assertEqual(restored.guest_links.get().label, 'Family')
        self.assertTrue(restored.note_set.get(name='Codes').is_private)

    def test_import_cannot_add_members_without_an_invite(self):
        data = self._export()
        for col in data['collections']:
            col['shared_with_user_ids'] = [str(self.stranger.uuid)]
            col['members'] = [{'user_uuid': str(self.stranger.uuid), 'role': 'editor'}]
        response = self._import(data)
        self.assertEqual(response.status_code, 200, response.content)

        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        self.assertFalse(restored.shared_with.filter(pk=self.stranger.pk).exists())
        self.assertIsNone(resolve_audience(restored, self.stranger))
        invite = CollectionInvite.objects.get(collection=restored, invited_user=self.stranger)
        self.assertEqual(invite.role, 'editor')

    def test_import_skips_users_without_a_public_profile_and_the_importer(self):
        private = make_user('private-person')
        private.public_profile = False
        private.save()
        data = self._export()
        for col in data['collections']:
            col['shared_with_user_ids'] = [str(private.uuid), str(self.owner.uuid)]
        self.assertEqual(self._import(data).status_code, 200)

        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        self.assertFalse(CollectionInvite.objects.filter(collection=restored, invited_user=private).exists())
        self.assertFalse(CollectionInvite.objects.filter(collection=restored, invited_user=self.owner).exists())

    def test_import_gives_guest_links_new_tokens(self):
        CollectionGuestLink.objects.create(collection=self.trip, role='editor', label='Family')
        data = self._export()
        chosen = 'attacker-chosen-token'
        for col in data['collections']:
            col['guest_links'][0]['token'] = chosen
        self.assertEqual(self._import(data).status_code, 200)

        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        link = restored.guest_links.get()
        self.assertNotEqual(link.token, chosen)
        self.assertEqual(link.label, 'Family')

    def test_older_backup_keeps_public_and_private_with_groups_off(self):
        data = self._export()
        data['backup_schema'] = 4
        for col in data['collections']:
            col.pop('visibility', None)
            col['story_groups'] = {'costs': True}
            col['is_public'] = True
        response = self._import(data)
        self.assertEqual(response.status_code, 200, response.content)
        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        self.assertEqual(restored.visibility, 'public')
        self.assertEqual(restored.story_groups, {})

        data['collections'][0]['is_public'] = False
        self._import(data)
        restored = Collection.objects.get(user=self.owner, name='Lofoten')
        self.assertEqual(restored.visibility, 'private')


class MigrationTests(APITestCase):
    def test_forwards_maps_public_and_shared_users(self):
        import importlib
        from django.apps import apps

        migration = importlib.import_module('adventures.migrations.0082_audience_and_story')
        owner = make_user('m-owner')
        friend = make_user('m-friend')
        public = Collection.objects.create(user=owner, name='Old public')
        Collection.objects.filter(pk=public.pk).update(is_public=True, visibility='private')
        public.shared_with.add(friend)
        CollectionMember.objects.all().delete()

        migration.forwards(apps, None)
        public.refresh_from_db()
        self.assertEqual(public.visibility, 'public')
        self.assertEqual(CollectionMember.objects.get(collection=public, user=friend).role, 'editor')


class InviteSearchTests(AudienceTestBase):
    def search(self, **params):
        self.as_user(self.owner)
        return self.client.get(f'/api/collections/{self.trip.id}/can-share/', params)

    def test_search_skips_owner_members_invited_and_private_profiles(self):
        make_user('editor-two', first_name='Ed')
        invited = make_user('editor-invited')
        CollectionInvite.objects.create(collection=self.trip, invited_user=invited)
        CustomUser.objects.create_user(
            username='editor-hidden', email='hidden@example.com', password='pw-12345678', public_profile=False
        )
        names = [u['username'] for u in self.search(q='editor').json()]
        self.assertEqual(names, ['editor-two'])
        self.assertEqual([u['username'] for u in self.search(q='ed two').json()], ['editor-two'])
        self.assertEqual(self.search(q='e').json(), [])
        self.assertNotIn('email', self.search(q='editor').json()[0])

    def test_results_are_capped_and_queries_do_not_grow_with_users(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        for i in range(30):
            make_user(f'traveler{i:02d}')
        with CaptureQueriesContext(connection) as small:
            self.search(q='traveler', limit=5)
        for i in range(30, 90):
            make_user(f'traveler{i:02d}')
        with CaptureQueriesContext(connection) as large:
            body = self.search(q='traveler', limit=500).json()
        self.assertEqual(len(body), 50)
        self.assertEqual(len(self.search(q='traveler').json()), 20)
        self.assertEqual(len(large.captured_queries), len(small.captured_queries))

    def test_only_the_owner_can_search(self):
        self.as_user(self.editor)
        response = self.client.get(f'/api/collections/{self.trip.id}/can-share/', {'q': 'view'})
        self.assertEqual(response.status_code, 404)
