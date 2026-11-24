"""Collections shown to everyone signed in to the server, and to nobody signed out (#621)."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from adventures.models import Activity, Collection, CollectionComment, Lodging
from adventures.utils.collection_type import imported_visibility
from adventures.tests.base import AudienceTestBase


@override_settings(ALLOW_PUBLIC_ACCESS=True)
class SignedInCollectionTests(AudienceTestBase):
    def setUp(self):
        super().setUp()
        self.hotel = Lodging.objects.create(user=self.owner, name='Rorbu', collection=self.trip, price=420)

    def read(self, user=None):
        self.client.force_authenticate(user=user)
        return self.client.get(f'/api/collections/{self.trip.id}/')

    def test_the_owner_can_show_a_collection_to_everyone_signed_in(self):
        self.as_user(self.owner)
        response = self.client.patch(f'/api/collections/{self.trip.id}/', {'visibility': 'signed_in'}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.trip.refresh_from_db()
        self.assertEqual((self.trip.visibility, self.trip.is_public), ('signed_in', False))

    @override_settings(ALLOW_PUBLIC_ACCESS=False)
    def test_it_is_allowed_on_a_server_without_public_access(self):
        self.as_user(self.owner)
        response = self.client.patch(f'/api/collections/{self.trip.id}/', {'visibility': 'signed_in'}, format='json')

        self.assertEqual(response.status_code, 200, response.content)

    def test_editors_cannot_change_who_sees_it(self):
        self.as_user(self.editor)
        response = self.client.patch(f'/api/collections/{self.trip.id}/', {'visibility': 'signed_in'}, format='json')

        self.assertIn(response.status_code, (400, 403, 404))
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.visibility, 'private')

    def test_signed_in_strangers_read_the_story_and_visitors_get_nothing(self):
        self.publish('signed_in')

        story = self.read(self.stranger)
        self.assertEqual(story.status_code, 200)
        self.assertEqual(story.json()['audience']['role'], 'public')
        self.assertNotIn('price', story.json()['lodging'][0], 'story groups still apply')
        self.assertEqual(self.read().status_code, 404)

    def test_members_still_get_the_private_plan(self):
        self.publish('signed_in')

        self.assertEqual(self.read(self.viewer).json()['audience']['role'], 'viewer')

    def test_it_is_listed_on_the_owners_profile_for_signed_in_users_only(self):
        self.owner.profile_visibility = 'public'
        self.owner.save()
        self.publish('signed_in')

        def listed(user=None):
            self.client.force_authenticate(user=user)
            return [c['name'] for c in self.client.get(f'/api/users/{self.owner.username}/').json()['collections']]

        self.assertEqual(listed(self.stranger), ['Lofoten'])
        self.assertEqual(listed(), [])

    def test_its_files_follow_the_same_rule(self):
        day = self.trip.itinerary_days.get(index=1)
        gpx = SimpleUploadedFile('ridge.gpx', b'<gpx></gpx>', content_type='application/gpx+xml')
        activity = Activity.objects.create(user=self.owner, day=day, name='Ridge', gpx_file=gpx)
        path = f'/media/{activity.gpx_file.name}'
        self.publish('signed_in', gpx=True)

        # Media is served by a plain Django view, so sign in with a real session.
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(path).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_signed_in_readers_can_read_its_story_comments(self):
        self.publish('signed_in')
        self.trip.comment_access = Collection.CommentAccess.SIGNED_IN
        self.trip.save()
        CollectionComment.objects.create(collection=self.trip, author_user=self.owner, body='Hi', is_story=True)

        self.as_user(self.stranger)
        response = self.client.get(f'/api/collections/{self.trip.id}/comments/', {'thread': 'story'})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([c['body'] for c in response.json()['comments']], ['Hi'])

    def test_a_backup_keeps_the_choice(self):
        self.assertEqual(imported_visibility('5', {'visibility': 'signed_in'}), 'signed_in')
