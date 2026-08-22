from rest_framework.test import APITestCase

from adventures.models import Collection, CollectionInvite
from users.models import CustomUser


class CollectionSharingPrivateProfileTestCase(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='collection-owner',
            email='collection-owner@example.com',
            password='testpassword123',
            public_profile=True,
            first_name='Collection',
            last_name='Owner',
        )
        self.collaborator = CustomUser.objects.create_user(
            username='collection-collab',
            email='collection-collab@example.com',
            password='testpassword123',
            public_profile=True,
            first_name='Shared',
            last_name='User',
        )
        self.collection = Collection.objects.create(
            user=self.owner,
            name='Shared Trip',
            description='Trip with a collaborator',
        )
        self.collection.shared_with.add(self.collaborator)

    def test_user_metadata_includes_sharing_counts(self):
        self.client.force_authenticate(user=self.collaborator)
        response = self.client.get('/auth/user-metadata/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['shared_collection_count'], 1)
        self.assertEqual(response.json()['pending_collection_invite_count'], 0)

    def test_making_profile_private_removes_existing_shares(self):
        self.client.force_authenticate(user=self.collaborator)
        response = self.client.patch(
            '/auth/update-user/',
            {'public_profile': False},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['left_shared_collections'], 1)
        self.collection.refresh_from_db()
        self.assertFalse(self.collection.shared_with.filter(id=self.collaborator.id).exists())

    def test_making_profile_private_revokes_pending_invites(self):
        other_collection = Collection.objects.create(
            user=self.owner,
            name='Pending Invite Trip',
        )
        CollectionInvite.objects.create(
            collection=other_collection,
            invited_user=self.collaborator,
        )

        self.client.force_authenticate(user=self.collaborator)
        response = self.client.patch(
            '/auth/update-user/',
            {'public_profile': False},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['revoked_collection_invites'], 1)
        self.assertFalse(
            CollectionInvite.objects.filter(
                collection=other_collection,
                invited_user=self.collaborator,
            ).exists()
        )

    def test_unshare_works_before_collaborator_goes_private(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/collections/{self.collection.id}/unshare/{self.collaborator.uuid}/'
        )

        self.assertEqual(response.status_code, 200)
        self.collection.refresh_from_db()
        self.assertFalse(self.collection.shared_with.filter(id=self.collaborator.id).exists())
