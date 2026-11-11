"""
Regression tests for privately reported advisories that the current code already closes.

Each test replays the advisory's proof of concept against the API and asserts the safe
outcome, so a refactor cannot quietly reopen it.
"""

import io
import json
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from adventures.models import CollectionInvite, CollectionItineraryItem, CollectionMember, Note
from adventures.tests.base import AudienceTestBase


class ItineraryCreateCollectionOwnershipTests(AudienceTestBase):
    """
    GHSA-8p3w-xcqv-7vvh, GHSA-q87p-c26r-6cqg, GHSA-vc29-j562-4hjq, GHSA-7vr6-67cp-v4m8 (itinerary part):
    placing your own record in someone else's collection.
    """

    def setUp(self):
        super().setUp()
        self.attacker_note = Note.objects.create(user=self.stranger, name='canary', content='canary')

    def place(self, user, collection):
        self.as_user(user)
        return self.client.post(
            f'/api/collections/{collection.id}/itinerary-items/',
            {'content_type': 'note', 'object_id': str(self.attacker_note.id), 'is_global': True},
            format='json',
        )

    def test_stranger_cannot_place_into_private_collection(self):
        response = self.place(self.stranger, self.trip)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(CollectionItineraryItem.objects.filter(object_id=str(self.attacker_note.id)).exists())

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_stranger_cannot_place_into_public_collection(self):
        self.publish('public')
        response = self.place(self.stranger, self.trip)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CollectionItineraryItem.objects.filter(object_id=str(self.attacker_note.id)).exists())

    def test_viewer_cannot_place_into_collection(self):
        self.attacker_note.user = self.viewer
        self.attacker_note.save()
        response = self.place(self.viewer, self.trip)
        self.assertEqual(response.status_code, 403)

    def test_numeric_content_type_is_rejected(self):
        self.as_user(self.stranger)
        response = self.client.post(
            f'/api/collections/{self.trip.id}/itinerary-items/',
            {'content_type': 7, 'object_id': str(self.attacker_note.id), 'is_global': True},
            format='json',
        )
        self.assertIn(response.status_code, (400, 404))


class NoteCollectionReassignmentTests(AudienceTestBase):
    """GHSA-7vr6-67cp-v4m8 (note part): a full PUT moving your note into someone else's collection."""

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_put_and_patch_cannot_move_a_note_into_a_foreign_collection(self):
        self.publish('public')
        note = Note.objects.create(user=self.stranger, name='canary', content='canary', is_public=True)
        self.as_user(self.stranger)

        put = self.client.put(
            f'/api/notes/{note.id}/',
            {'name': 'canary', 'content': 'canary', 'is_public': True, 'collection': str(self.trip.id)},
            format='json',
        )
        patch = self.client.patch(f'/api/notes/{note.id}/', {'collection': str(self.trip.id)}, format='json')

        self.assertEqual(put.status_code, 403)
        self.assertEqual(patch.status_code, 403)
        note.refresh_from_db()
        self.assertIsNone(note.collection_id)


class CollectionVisibilityTests(AudienceTestBase):
    """GHSA-x7c9-c8gj-563q: a collaborator publishing the owner's private collection."""

    @override_settings(ALLOW_PUBLIC_COLLECTION_LINKS=True)
    def test_editor_cannot_publish_and_nothing_cascades(self):
        self.as_user(self.editor)
        for body in ({'visibility': 'public'}, {'is_public': True}):
            with self.subTest(body=body):
                response = self.client.patch(f'/api/collections/{self.trip.id}/', body, format='json')
                self.assertIn(response.status_code, (403, 404))
        self.trip.refresh_from_db()
        self.hut.refresh_from_db()
        self.assertEqual(self.trip.visibility, 'private')
        self.assertFalse(self.hut.is_public)


class BackupImportShareConsentTests(AudienceTestBase):
    """GHSA-mcrf-2xj6-8f3w (consent part): a crafted backup adding a victim to a collection."""

    def test_shared_with_ids_in_a_backup_become_pending_invites(self):
        victim = self.viewer
        data = {
            'version': 'v0.13.0',
            'collections': [{
                'export_id': 0, 'name': 'forced-share', 'description': '', 'is_public': False,
                'start_date': None, 'end_date': None, 'is_archived': False, 'link': None,
                'shared_with_user_ids': [str(victim.uuid)],
                'members': [{'user_uuid': str(victim.uuid), 'role': 'editor'}],
            }],
            'notes': [{
                'export_id': 0, 'name': 'x', 'content': '<img src=x onerror=alert(1)>', 'links': [],
                'date': None, 'is_public': False, 'collection_export_id': 0,
            }],
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('data.json', json.dumps(data))
        upload = SimpleUploadedFile('backup.zip', buffer.getvalue(), content_type='application/zip')

        self.as_user(self.stranger)
        response = self.client.post('/api/backup/import/', {'file': upload, 'confirm': 'yes'}, format='multipart')
        self.assertEqual(response.status_code, 200, response.content)

        imported = self.stranger.collection_set.get(name='forced-share')
        self.assertFalse(imported.shared_with.filter(pk=victim.pk).exists())
        self.assertFalse(CollectionMember.objects.filter(collection=imported, user=victim).exists())
        self.assertTrue(CollectionInvite.objects.filter(collection=imported, invited_user=victim).exists())

        self.as_user(victim)
        self.assertEqual(self.client.get(f'/api/collections/{imported.id}/').status_code, 404)
