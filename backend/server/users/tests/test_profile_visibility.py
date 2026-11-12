"""Profiles shown to signed-in users only (#1226), and the server-wide switch (#1124), through the API."""

from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionComment, CollectionInvite
from core.testing import make_user


class ProfilePageTests(APITestCase):
    def setUp(self):
        self.viewer = make_user('page-viewer')
        self.member_only = make_user('page-signed-in', profile_visibility='signed_in')
        self.public = make_user('page-public', profile_visibility='public')
        self.private = make_user('page-private')

    def page(self, person, user=None):
        self.client.force_authenticate(user=user)
        return self.client.get(f'/api/users/{person.username}/')

    def listed(self, user=None):
        self.client.force_authenticate(user=user)
        return sorted(p['username'] for p in self.client.get('/api/users/').json())

    def test_a_profile_for_signed_in_users_opens_for_them_and_not_for_visitors(self):
        self.assertEqual(self.page(self.member_only, self.viewer).status_code, 200)
        self.assertEqual(self.page(self.member_only).status_code, 404)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(f'/api/users/{self.member_only.username}/stats/').status_code, 404)

    def test_the_people_list_shows_signed_in_profiles_to_signed_in_users_only(self):
        self.assertEqual(self.listed(self.viewer), ['page-public', 'page-signed-in'])
        self.assertEqual(self.listed(), ['page-public'])

    def test_a_private_profile_stays_hidden_from_everyone_else(self):
        self.assertEqual(self.page(self.private, self.viewer).status_code, 404)
        self.assertEqual(self.page(self.private, self.private).status_code, 200)

    def test_the_profile_says_who_it_is_shown_to(self):
        self.assertEqual(self.page(self.member_only, self.viewer).json()['user']['profile_visibility'], 'signed_in')

    @override_settings(ALLOW_PUBLIC_ACCESS=False)
    def test_without_public_access_visitors_see_no_profiles(self):
        self.assertEqual(self.page(self.public).status_code, 404)
        self.assertEqual(self.listed(), [])
        self.assertEqual(self.page(self.public, self.viewer).status_code, 200)


class ProfileSettingTests(APITestCase):
    def setUp(self):
        self.owner = make_user('set-owner', profile_visibility='public')
        self.person = make_user('set-person', profile_visibility='public')
        self.trip = Collection.objects.create(user=self.owner, name='Shared trip')
        self.trip.shared_with.add(self.person)
        self.client.force_authenticate(user=self.person)

    def patch(self, **data):
        return self.client.patch('/api/account/', data, format='json')

    def still_shared(self):
        return self.trip.shared_with.filter(id=self.person.id).exists()

    def test_showing_the_profile_to_signed_in_users_only_keeps_shared_collections(self):
        response = self.patch(profile_visibility='signed_in')

        self.assertEqual(response.status_code, 200, response.content)
        self.person.refresh_from_db()
        self.assertEqual((self.person.profile_visibility, self.person.public_profile), ('signed_in', False))
        self.assertTrue(self.still_shared())
        self.assertIsNone(response.json().get('left_shared_collections'))

    def test_making_the_profile_private_leaves_shared_collections(self):
        self.patch(profile_visibility='signed_in')

        response = self.patch(profile_visibility='private')

        self.assertEqual(response.json()['left_shared_collections'], 1)
        self.assertFalse(self.still_shared())

    def test_an_old_client_turning_public_off_keeps_a_signed_in_profile_and_its_shares(self):
        self.patch(profile_visibility='signed_in')

        response = self.patch(public_profile=False)

        self.assertEqual(response.status_code, 200)
        self.person.refresh_from_db()
        self.assertEqual(self.person.profile_visibility, 'signed_in')
        self.assertTrue(self.still_shared())

    def test_an_old_client_turning_public_off_still_makes_a_public_profile_private(self):
        response = self.patch(public_profile=False)

        self.assertEqual(response.json()['left_shared_collections'], 1)
        self.person.refresh_from_db()
        self.assertEqual(self.person.profile_visibility, 'private')


class InviteTests(APITestCase):
    def setUp(self):
        self.owner = make_user('inv-owner')
        self.member_only = make_user('inv-signed-in', profile_visibility='signed_in')
        self.private = make_user('inv-private')
        self.trip = Collection.objects.create(user=self.owner, name='Trip')
        self.client.force_authenticate(user=self.owner)

    def test_people_with_a_profile_for_signed_in_users_can_be_found_and_invited(self):
        found = self.client.get(f'/api/collections/{self.trip.id}/shareable-users/', {'q': 'inv'}).json()
        self.assertEqual([p['username'] for p in found], ['inv-signed-in'])

        response = self.client.post(
            f'/api/collections/{self.trip.id}/invites/', {'user': str(self.member_only.uuid)}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(CollectionInvite.objects.filter(collection=self.trip, invited_user=self.member_only).exists())

    def test_people_with_a_private_profile_cannot_be_invited(self):
        response = self.client.post(
            f'/api/collections/{self.trip.id}/invites/', {'user': str(self.private.uuid)}, format='json'
        )
        self.assertEqual(response.status_code, 404)


class PeopleSearchTests(APITestCase):
    def test_signed_in_users_find_profiles_shown_to_signed_in_users(self):
        make_user('findme-signed-in', profile_visibility='signed_in')
        make_user('findme-private')
        self.client.force_authenticate(user=make_user('searcher'))

        results = self.client.get('/api/search/', {'q': 'findme', 'types': 'user'}).json()['results']

        self.assertEqual([hit['label'] if 'label' in hit else hit.get('title') for hit in results if hit['type'] == 'user'],
                         ['findme-signed-in'])


@override_settings(ALLOW_PUBLIC_ACCESS=True)
class PeopleOnAStoryTests(APITestCase):
    """The owner and commenters of a public story are named when the reader may see their profile."""

    def setUp(self):
        self.owner = make_user('story-owner', profile_visibility='signed_in')
        self.trip = Collection.objects.create(user=self.owner, name='Open trip', visibility='public')
        self.reader = make_user('story-reader')

    def story(self, user=None):
        self.client.force_authenticate(user=user)
        return self.client.get(f'/api/collections/{self.trip.id}/').json()

    def test_a_signed_in_reader_sees_an_owner_whose_profile_is_for_signed_in_users(self):
        self.assertEqual([c['username'] for c in self.story(self.reader)['collaborators']], ['story-owner'])

    def test_a_visitor_does_not(self):
        self.assertEqual(self.story()['collaborators'], [])

    def test_commenters_are_shown_by_the_same_rule(self):
        self.trip.comment_access = 'signed_in'
        self.trip.save()
        CollectionComment.objects.create(collection=self.trip, author_user=self.owner, body='Hello', is_story=True)

        def author(user=None):
            self.client.force_authenticate(user=user)
            response = self.client.get(f'/api/collections/{self.trip.id}/comments/', {'thread': 'story'})
            return response.json()['comments'][0]['author']

        self.assertEqual(author(self.reader)['username'], 'story-owner')
        self.assertTrue(author(self.reader)['can_view_profile'])
        self.assertIsNone(author()['username'])
