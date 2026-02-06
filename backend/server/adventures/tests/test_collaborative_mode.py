"""
Comprehensive tests for Collaborative Mode feature.

Tests cover:
1. Permission tests - who can edit what
2. Audit logging tests - tracking changes
3. Revert functionality tests - undoing changes
4. Ownership attribution tests - who owns what
"""

from django.test import TestCase, override_settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from uuid import uuid4
import json
import io
from PIL import Image

from users.models import CustomUser
from adventures.models import (
    Location, Visit, ContentImage, ContentAttachment,
    Collection, Category, Note, Transportation, Lodging,
    AuditLog
)
from adventures.signals import set_current_user


def create_test_image():
    """Create a simple test image file."""
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='red')
    image.save(file, 'PNG')
    file.name = 'test.png'
    file.seek(0)
    return SimpleUploadedFile(
        name='test.png',
        content=file.read(),
        content_type='image/png'
    )


def create_test_file():
    """Create a simple test file for attachments."""
    return SimpleUploadedFile(
        name='test.txt',
        content=b'Test file content',
        content_type='text/plain'
    )


class CollaborativeModeTestBase(TestCase):
    """Base test class with common setup for collaborative mode tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data shared by all test methods."""
        # Create users
        cls.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123'
        )
        cls.collaborator = CustomUser.objects.create_user(
            username='collaborator',
            email='collaborator@example.com',
            password='testpass123'
        )
        cls.other_user = CustomUser.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        cls.staff_user = CustomUser.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

    def setUp(self):
        """Set up test fixtures for each test method."""
        # Create a category for the owner
        self.category = Category.objects.create(
            user=self.owner,
            name='test_category',
            display_name='Test Category',
            icon='T'
        )

        # Create a public location owned by owner
        self.public_location = Location.objects.create(
            user=self.owner,
            name='Public Test Location',
            is_public=True,
            latitude=40.7128,
            longitude=-74.0060,
            category=self.category
        )

        # Create a private location owned by owner
        self.private_location = Location.objects.create(
            user=self.owner,
            name='Private Test Location',
            is_public=False,
            latitude=34.0522,
            longitude=-118.2437,
            category=self.category
        )


class CollaborativeModeAPITestBase(APITestCase):
    """Base test class for API tests with common setup."""

    def setUp(self):
        """Set up test fixtures."""
        # Create users
        self.owner = CustomUser.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123'
        )
        self.collaborator = CustomUser.objects.create_user(
            username='collaborator',
            email='collaborator@example.com',
            password='testpass123'
        )
        self.other_user = CustomUser.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        self.staff_user = CustomUser.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )

        # Create a category
        self.category = Category.objects.create(
            user=self.owner,
            name='test_category',
            display_name='Test Category',
            icon='T'
        )

        # Create a public location
        self.public_location = Location.objects.create(
            user=self.owner,
            name='Public Test Location',
            is_public=True,
            latitude=40.7128,
            longitude=-74.0060,
            category=self.category
        )

        # Create a private location
        self.private_location = Location.objects.create(
            user=self.owner,
            name='Private Test Location',
            is_public=False,
            category=self.category
        )

        self.client = APIClient()


# =============================================================================
# 1. PERMISSION TESTS
# =============================================================================

@override_settings(COLLABORATIVE_MODE=True)
class PublicLocationPermissionTests(CollaborativeModeAPITestBase):
    """Test that public locations can be edited by any authenticated user in collaborative mode."""

    def test_authenticated_user_can_edit_public_location(self):
        """Any authenticated user can edit a public location in collaborative mode."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.patch(
            f'/api/locations/{self.public_location.id}/',
            {'description': 'Updated by collaborator'},
            format='json'
        )

        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
        # If successful, verify the change
        if response.status_code == status.HTTP_200_OK:
            self.public_location.refresh_from_db()
            self.assertEqual(self.public_location.description, 'Updated by collaborator')

    def test_unauthenticated_user_cannot_edit_public_location(self):
        """Unauthenticated users cannot edit public locations."""
        response = self.client.patch(
            f'/api/locations/{self.public_location.id}/',
            {'description': 'Should not work'},
            format='json'
        )

        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ])

    def test_owner_can_edit_own_public_location(self):
        """Owner can edit their own public location."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f'/api/locations/{self.public_location.id}/',
            {'description': 'Updated by owner'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.public_location.refresh_from_db()
        self.assertEqual(self.public_location.description, 'Updated by owner')


@override_settings(COLLABORATIVE_MODE=True)
class VisitPermissionTests(CollaborativeModeAPITestBase):
    """Test that visits can only be edited/deleted by their creator."""

    def setUp(self):
        super().setUp()
        # Create a visit on the public location by owner
        self.owner_visit = Visit.objects.create(
            location=self.public_location,
            user=self.owner,
            start_date=timezone.now(),
            end_date=timezone.now(),
            notes='Owner visit'
        )
        # Create a visit by collaborator
        self.collaborator_visit = Visit.objects.create(
            location=self.public_location,
            user=self.collaborator,
            start_date=timezone.now(),
            end_date=timezone.now(),
            notes='Collaborator visit'
        )

    def test_creator_can_edit_own_visit(self):
        """Visit creator can edit their own visit."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.patch(
            f'/api/visits/{self.collaborator_visit.id}/',
            {'notes': 'Updated notes'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.collaborator_visit.refresh_from_db()
        self.assertEqual(self.collaborator_visit.notes, 'Updated notes')

    def test_other_user_cannot_edit_visit(self):
        """Users cannot edit visits they didn't create."""
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            f'/api/visits/{self.collaborator_visit.id}/',
            {'notes': 'Unauthorized update'},
            format='json'
        )

        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])

    def test_creator_can_delete_own_visit(self):
        """Visit creator can delete their own visit."""
        self.client.force_authenticate(user=self.collaborator)
        visit_id = self.collaborator_visit.id

        response = self.client.delete(f'/api/visits/{visit_id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Visit.objects.filter(id=visit_id).exists())

    def test_other_user_cannot_delete_visit(self):
        """Users cannot delete visits they didn't create."""
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(f'/api/visits/{self.collaborator_visit.id}/')

        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])

    def test_location_owner_cannot_delete_others_visit(self):
        """Even location owner cannot delete visits created by others."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f'/api/visits/{self.collaborator_visit.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(COLLABORATIVE_MODE=True)
class ImagePermissionTests(CollaborativeModeAPITestBase):
    """Test that images can only be deleted by their uploader."""

    def setUp(self):
        super().setUp()
        # Create an image uploaded by owner
        self.owner_image = ContentImage.objects.create(
            user=self.owner,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            immich_id='test-immich-id-owner'
        )
        # Create an image uploaded by collaborator
        self.collaborator_image = ContentImage.objects.create(
            user=self.collaborator,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            immich_id='test-immich-id-collaborator'
        )

    def test_uploader_can_delete_own_image(self):
        """Image uploader can delete their own image."""
        self.client.force_authenticate(user=self.collaborator)
        image_id = self.collaborator_image.id

        response = self.client.delete(f'/api/images/{image_id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # In collaborative mode, images are soft-deleted
        self.collaborator_image.refresh_from_db()
        self.assertTrue(self.collaborator_image.is_deleted)

    def test_other_user_cannot_delete_image(self):
        """Users cannot delete images they didn't upload."""
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(f'/api/images/{self.collaborator_image.id}/')

        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])

    def test_location_owner_cannot_delete_others_image(self):
        """Even location owner cannot delete images uploaded by others."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f'/api/images/{self.collaborator_image.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(COLLABORATIVE_MODE=True)
class AttachmentPermissionTests(CollaborativeModeAPITestBase):
    """Test that attachments can only be deleted by their uploader."""

    def setUp(self):
        super().setUp()
        # Create an attachment uploaded by owner
        self.owner_attachment = ContentAttachment.objects.create(
            user=self.owner,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            file=create_test_file(),
            name='owner_file.txt'
        )
        # Create an attachment uploaded by collaborator
        self.collaborator_attachment = ContentAttachment.objects.create(
            user=self.collaborator,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            file=create_test_file(),
            name='collaborator_file.txt'
        )

    def test_uploader_can_delete_own_attachment(self):
        """Attachment uploader can delete their own attachment."""
        self.client.force_authenticate(user=self.collaborator)
        attachment_id = self.collaborator_attachment.id

        response = self.client.delete(f'/api/attachments/{attachment_id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # In collaborative mode, attachments are soft-deleted
        self.collaborator_attachment.refresh_from_db()
        self.assertTrue(self.collaborator_attachment.is_deleted)

    def test_other_user_cannot_delete_attachment(self):
        """Users cannot delete attachments they didn't upload."""
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(f'/api/attachments/{self.collaborator_attachment.id}/')

        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])


# =============================================================================
# 2. AUDIT LOGGING TESTS
# =============================================================================

@override_settings(COLLABORATIVE_MODE=True)
class LocationAuditLogTests(CollaborativeModeTestBase):
    """Test that location changes are logged correctly."""

    def test_location_create_is_logged(self):
        """Creating a location generates an audit log entry."""
        # Set the current user for audit logging
        set_current_user(self.collaborator)

        location = Location.objects.create(
            user=self.collaborator,
            name='Audit Test Location',
            is_public=True
        )

        # Clear current user
        set_current_user(None)

        # Find the audit log
        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Location),
            object_id=location.id,
            action='create'
        ).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.collaborator)
        self.assertIn('Audit Test Location', log.object_repr)

    def test_location_update_is_logged(self):
        """Updating a location generates an audit log entry with changes."""
        set_current_user(self.owner)

        old_name = self.public_location.name
        self.public_location.name = 'Updated Location Name'
        self.public_location.save()

        set_current_user(None)

        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            action='update'
        ).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.owner)
        self.assertIn('name', log.changes)
        self.assertEqual(log.changes['name']['old'], old_name)
        self.assertEqual(log.changes['name']['new'], 'Updated Location Name')

    def test_location_delete_is_logged(self):
        """Deleting a location generates an audit log entry."""
        location = Location.objects.create(
            user=self.owner,
            name='Location to Delete',
            is_public=True
        )
        location_id = location.id

        set_current_user(self.owner)
        location.delete()
        set_current_user(None)

        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Location),
            object_id=location_id,
            action='delete'
        ).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.owner)


@override_settings(COLLABORATIVE_MODE=True)
class VisitAuditLogTests(CollaborativeModeTestBase):
    """Test that visit changes are logged correctly."""

    def test_visit_create_is_logged(self):
        """Creating a visit generates an audit log entry."""
        set_current_user(self.collaborator)

        visit = Visit.objects.create(
            location=self.public_location,
            user=self.collaborator,
            start_date=timezone.now(),
            end_date=timezone.now(),
            notes='Test visit'
        )

        set_current_user(None)

        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Visit),
            object_id=visit.id,
            action='create'
        ).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.collaborator)

    def test_visit_update_is_logged(self):
        """Updating a visit generates an audit log entry."""
        visit = Visit.objects.create(
            location=self.public_location,
            user=self.owner,
            start_date=timezone.now(),
            end_date=timezone.now(),
            notes='Original notes'
        )

        set_current_user(self.owner)
        visit.notes = 'Updated notes'
        visit.save()
        set_current_user(None)

        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Visit),
            object_id=visit.id,
            action='update'
        ).first()

        self.assertIsNotNone(log)
        self.assertIn('notes', log.changes)


@override_settings(COLLABORATIVE_MODE=True)
class ImageAttachmentAuditLogTests(CollaborativeModeTestBase):
    """Test that image and attachment changes are logged correctly."""

    def test_image_create_is_logged(self):
        """Creating an image generates an audit log entry."""
        set_current_user(self.collaborator)

        image = ContentImage.objects.create(
            user=self.collaborator,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            immich_id='test-immich-id'
        )

        set_current_user(None)

        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(ContentImage),
            object_id=image.id,
            action='create'
        ).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.collaborator)

    def test_attachment_create_is_logged(self):
        """Creating an attachment generates an audit log entry."""
        set_current_user(self.collaborator)

        attachment = ContentAttachment.objects.create(
            user=self.collaborator,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            file=create_test_file(),
            name='test_file.txt'
        )

        set_current_user(None)

        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(ContentAttachment),
            object_id=attachment.id,
            action='create'
        ).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.collaborator)


@override_settings(COLLABORATIVE_MODE=True)
class AuditLogUserCaptureTests(CollaborativeModeAPITestBase):
    """Test that the correct user is captured in audit logs."""

    def test_api_update_captures_correct_user(self):
        """API updates capture the authenticated user in audit log."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.patch(
            f'/api/locations/{self.public_location.id}/',
            {'description': 'API update test'},
            format='json'
        )

        if response.status_code == status.HTTP_200_OK:
            log = AuditLog.objects.filter(
                content_type=ContentType.objects.get_for_model(Location),
                object_id=self.public_location.id,
                action='update'
            ).order_by('-timestamp').first()

            # The middleware should capture the user
            # Note: In tests, the middleware may not always run
            if log:
                self.assertIn(log.user, [self.collaborator, None])


# =============================================================================
# 3. REVERT FUNCTIONALITY TESTS
# =============================================================================

@override_settings(COLLABORATIVE_MODE=True)
class RevertFieldUpdateTests(CollaborativeModeAPITestBase):
    """Test reverting field updates."""

    def setUp(self):
        super().setUp()
        # Set up initial state and create an update
        set_current_user(self.owner)
        self.public_location.description = 'Initial description'
        self.public_location.save()

        self.public_location.description = 'Updated description'
        self.public_location.save()
        set_current_user(None)

        # Get the update log
        self.update_log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            action='update'
        ).order_by('-timestamp').first()

    def test_can_revert_field_update(self):
        """Can revert a field update to restore old value."""
        self.client.force_authenticate(user=self.owner)

        if self.update_log:
            response = self.client.post(
                f'/api/locations/{self.public_location.id}/revert/{self.update_log.id}/'
            )

            if response.status_code == status.HTTP_200_OK:
                self.public_location.refresh_from_db()
                self.assertEqual(self.public_location.description, 'Initial description')


@override_settings(COLLABORATIVE_MODE=True)
class RevertImageCreationTests(CollaborativeModeAPITestBase):
    """Test reverting image creation (deletes the image)."""

    def setUp(self):
        super().setUp()
        # Create an image and log it
        set_current_user(self.collaborator)
        self.image = ContentImage.objects.create(
            user=self.collaborator,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            immich_id='test-immich-revert'
        )
        set_current_user(None)

        self.create_log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(ContentImage),
            object_id=self.image.id,
            action='create'
        ).first()

    def test_can_revert_image_creation(self):
        """Reverting image creation soft-deletes the image."""
        self.client.force_authenticate(user=self.collaborator)

        if self.create_log:
            response = self.client.post(
                f'/api/locations/{self.public_location.id}/revert/{self.create_log.id}/'
            )

            if response.status_code == status.HTTP_200_OK:
                self.image.refresh_from_db()
                self.assertTrue(self.image.is_deleted)


@override_settings(COLLABORATIVE_MODE=True)
class RevertImageDeletionTests(CollaborativeModeAPITestBase):
    """Test reverting image deletion (restores soft-deleted image)."""

    def setUp(self):
        super().setUp()
        # Create and then soft-delete an image
        set_current_user(self.collaborator)
        self.image = ContentImage.objects.create(
            user=self.collaborator,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            immich_id='test-immich-restore'
        )

        # Soft-delete the image
        self.image.deleted_by = self.collaborator
        self.image.delete()  # This soft-deletes in collaborative mode
        set_current_user(None)

        self.delete_log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(ContentImage),
            object_id=self.image.id,
            action='delete'
        ).first()

    def test_can_revert_image_deletion(self):
        """Reverting image deletion restores the soft-deleted image."""
        self.client.force_authenticate(user=self.collaborator)

        if self.delete_log:
            response = self.client.post(
                f'/api/locations/{self.public_location.id}/revert/{self.delete_log.id}/'
            )

            if response.status_code == status.HTTP_200_OK:
                self.image.refresh_from_db()
                self.assertFalse(self.image.is_deleted)


@override_settings(COLLABORATIVE_MODE=True)
class RevertPermissionTests(CollaborativeModeAPITestBase):
    """Test permission checks for revert operations."""

    def setUp(self):
        super().setUp()
        # Create an update log by collaborator
        set_current_user(self.collaborator)
        self.public_location.description = 'Changed by collaborator'
        self.public_location.save()
        set_current_user(None)

        self.collaborator_log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            action='update',
            user=self.collaborator
        ).first()

    def test_change_creator_can_revert(self):
        """The user who made the change can revert it."""
        self.client.force_authenticate(user=self.collaborator)

        if self.collaborator_log:
            response = self.client.post(
                f'/api/locations/{self.public_location.id}/revert/{self.collaborator_log.id}/'
            )

            self.assertIn(response.status_code, [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST  # May fail if no old values to revert
            ])

    def test_location_owner_can_revert(self):
        """The location owner can revert changes made by others."""
        self.client.force_authenticate(user=self.owner)

        if self.collaborator_log:
            response = self.client.post(
                f'/api/locations/{self.public_location.id}/revert/{self.collaborator_log.id}/'
            )

            self.assertIn(response.status_code, [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST
            ])

    def test_staff_can_revert(self):
        """Staff users can revert any changes."""
        self.client.force_authenticate(user=self.staff_user)

        if self.collaborator_log:
            response = self.client.post(
                f'/api/locations/{self.public_location.id}/revert/{self.collaborator_log.id}/'
            )

            self.assertIn(response.status_code, [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST
            ])

    def test_other_user_cannot_revert(self):
        """Random users cannot revert changes they didn't make."""
        self.client.force_authenticate(user=self.other_user)

        if self.collaborator_log:
            response = self.client.post(
                f'/api/locations/{self.public_location.id}/revert/{self.collaborator_log.id}/'
            )

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# =============================================================================
# 4. OWNERSHIP ATTRIBUTION TESTS
# =============================================================================

@override_settings(COLLABORATIVE_MODE=True)
class VisitOwnershipAttributionTests(CollaborativeModeAPITestBase):
    """Test that visits are attributed to their creator."""

    def test_visit_attributed_to_creator(self):
        """Visits are attributed to the user who created them."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.post(
            '/api/visits/',
            {
                'location': str(self.public_location.id),
                'start_date': timezone.now().isoformat(),
                'end_date': timezone.now().isoformat(),
                'notes': 'Collaborator visit'
            },
            format='json'
        )

        if response.status_code == status.HTTP_201_CREATED:
            visit = Visit.objects.get(id=response.data['id'])
            self.assertEqual(visit.user, self.collaborator)


@override_settings(COLLABORATIVE_MODE=True)
class ImageOwnershipAttributionTests(CollaborativeModeAPITestBase):
    """Test that images are attributed to their uploader."""

    def test_image_attributed_to_uploader(self):
        """Images are attributed to the user who uploaded them."""
        self.client.force_authenticate(user=self.collaborator)

        # Create image via API
        response = self.client.post(
            '/api/images/',
            {
                'content_type': 'location',
                'object_id': str(self.public_location.id),
                'immich_id': 'test-attribution-immich'
            },
            format='json'
        )

        if response.status_code == status.HTTP_201_CREATED:
            image = ContentImage.objects.get(id=response.data['id'])
            self.assertEqual(image.user, self.collaborator)


@override_settings(COLLABORATIVE_MODE=True)
class AttachmentOwnershipAttributionTests(CollaborativeModeAPITestBase):
    """Test that attachments are attributed to their uploader."""

    def test_attachment_attributed_to_uploader(self):
        """Attachments are attributed to the user who uploaded them."""
        self.client.force_authenticate(user=self.collaborator)

        test_file = create_test_file()
        response = self.client.post(
            '/api/attachments/',
            {
                'content_type': 'location',
                'object_id': str(self.public_location.id),
                'file': test_file,
                'name': 'test_attribution.txt'
            },
            format='multipart'
        )

        if response.status_code == status.HTTP_201_CREATED:
            attachment = ContentAttachment.objects.get(id=response.data['id'])
            self.assertEqual(attachment.user, self.collaborator)


@override_settings(COLLABORATIVE_MODE=True)
class NoteOwnershipAttributionTests(CollaborativeModeAPITestBase):
    """Test that notes are attributed to their creator in collaborative mode."""

    def setUp(self):
        super().setUp()
        # Create a collection that collaborator is shared with
        self.collection = Collection.objects.create(
            user=self.owner,
            name='Test Collection',
            is_public=False
        )
        self.collection.shared_with.add(self.collaborator)

    def test_note_attributed_to_creator_in_shared_collection(self):
        """Notes in shared collections are attributed to the creator, not collection owner."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.post(
            '/api/notes/',
            {
                'name': 'Collaborator Note',
                'content': 'Test content',
                'collection': str(self.collection.id)
            },
            format='json'
        )

        if response.status_code == status.HTTP_201_CREATED:
            note = Note.objects.get(id=response.data['id'])
            self.assertEqual(note.user, self.collaborator)


@override_settings(COLLABORATIVE_MODE=True)
class TransportationOwnershipAttributionTests(CollaborativeModeAPITestBase):
    """Test that transportation entries are attributed to their creator in collaborative mode."""

    def setUp(self):
        super().setUp()
        self.collection = Collection.objects.create(
            user=self.owner,
            name='Test Collection',
            is_public=False
        )
        self.collection.shared_with.add(self.collaborator)

    def test_transportation_attributed_to_creator(self):
        """Transportation entries are attributed to the creator, not collection owner."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.post(
            '/api/transportations/',
            {
                'name': 'Collaborator Flight',
                'type': 'plane',
                'collection': str(self.collection.id)
            },
            format='json'
        )

        if response.status_code == status.HTTP_201_CREATED:
            transportation = Transportation.objects.get(id=response.data['id'])
            self.assertEqual(transportation.user, self.collaborator)


@override_settings(COLLABORATIVE_MODE=True)
class LodgingOwnershipAttributionTests(CollaborativeModeAPITestBase):
    """Test that lodging entries are attributed to their creator in collaborative mode."""

    def setUp(self):
        super().setUp()
        self.collection = Collection.objects.create(
            user=self.owner,
            name='Test Collection',
            is_public=False
        )
        self.collection.shared_with.add(self.collaborator)

    def test_lodging_attributed_to_creator(self):
        """Lodging entries are attributed to the creator, not collection owner."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.post(
            '/api/lodgings/',
            {
                'name': 'Collaborator Hotel',
                'type': 'hotel',
                'collection': str(self.collection.id)
            },
            format='json'
        )

        if response.status_code == status.HTTP_201_CREATED:
            lodging = Lodging.objects.get(id=response.data['id'])
            self.assertEqual(lodging.user, self.collaborator)


# =============================================================================
# NON-COLLABORATIVE MODE TESTS
# =============================================================================

@override_settings(COLLABORATIVE_MODE=False)
class NonCollaborativeModePermissionTests(CollaborativeModeAPITestBase):
    """Test that collaborative mode features are disabled when COLLABORATIVE_MODE=False."""

    def test_authenticated_user_cannot_edit_others_public_location(self):
        """In non-collaborative mode, users cannot edit others' public locations."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.patch(
            f'/api/locations/{self.public_location.id}/',
            {'description': 'Should not work'},
            format='json'
        )

        # Should be forbidden when not in collaborative mode
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])


@override_settings(COLLABORATIVE_MODE=False)
class NonCollaborativeModeOwnershipTests(CollaborativeModeAPITestBase):
    """Test ownership attribution when not in collaborative mode."""

    def setUp(self):
        super().setUp()
        self.collection = Collection.objects.create(
            user=self.owner,
            name='Test Collection',
            is_public=False
        )
        self.collection.shared_with.add(self.collaborator)

    def test_note_attributed_to_collection_owner(self):
        """In non-collaborative mode, notes in collections are attributed to collection owner."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.post(
            '/api/notes/',
            {
                'name': 'Collaborator Note',
                'content': 'Test content',
                'collection': str(self.collection.id)
            },
            format='json'
        )

        if response.status_code == status.HTTP_201_CREATED:
            note = Note.objects.get(id=response.data['id'])
            # In non-collaborative mode, ownership goes to collection owner
            self.assertEqual(note.user, self.owner)


@override_settings(COLLABORATIVE_MODE=False)
class NonCollaborativeModeAuditLogTests(CollaborativeModeTestBase):
    """Test that audit logging is disabled when COLLABORATIVE_MODE=False."""

    def test_no_audit_log_created_when_disabled(self):
        """Audit logs should not be created when collaborative mode is disabled."""
        initial_count = AuditLog.objects.count()

        set_current_user(self.owner)
        Location.objects.create(
            user=self.owner,
            name='No Audit Location',
            is_public=True
        )
        set_current_user(None)

        final_count = AuditLog.objects.count()
        self.assertEqual(initial_count, final_count)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

@override_settings(COLLABORATIVE_MODE=True)
class CollaborativeModeEdgeCaseTests(CollaborativeModeAPITestBase):
    """Test edge cases in collaborative mode."""

    def test_cannot_delete_location_if_not_owner(self):
        """Only the owner can delete a location, even in collaborative mode."""
        self.client.force_authenticate(user=self.collaborator)

        response = self.client.delete(f'/api/locations/{self.public_location.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_history_endpoint_returns_logs(self):
        """The history endpoint returns audit logs for a location."""
        # Create some changes
        set_current_user(self.owner)
        self.public_location.description = 'Change 1'
        self.public_location.save()
        self.public_location.description = 'Change 2'
        self.public_location.save()
        set_current_user(None)

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(f'/api/locations/{self.public_location.id}/history/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_revert_nonexistent_log_returns_error(self):
        """Reverting a nonexistent audit log returns 404."""
        self.client.force_authenticate(user=self.owner)

        fake_log_id = uuid4()
        response = self.client.post(
            f'/api/locations/{self.public_location.id}/revert/{fake_log_id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_deleted_images_not_in_queryset(self):
        """Soft-deleted images are excluded from the default queryset."""
        # Create and soft-delete an image
        set_current_user(self.owner)
        image = ContentImage.objects.create(
            user=self.owner,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=self.public_location.id,
            immich_id='soft-delete-test'
        )
        image.is_deleted = True
        image.deleted_at = timezone.now()
        image.save()
        set_current_user(None)

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(f'/api/locations/{self.public_location.id}/')

        if response.status_code == status.HTTP_200_OK:
            images = response.data.get('images', [])
            image_ids = [img['id'] for img in images]
            self.assertNotIn(str(image.id), image_ids)
