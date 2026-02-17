"""
Model mixins for common patterns across Location, Transportation, Lodging, etc.
"""

import os
from django.conf import settings
from django.utils import timezone


class MediaDeletionMixin:
    """
    Mixin that deletes all associated images and attachments before deleting the model instance.

    Requires the model to have 'images' and 'attachments' GenericRelation fields.

    Used by: Visit, Location, Transportation, Note, Lodging
    """

    def delete(self, *args, **kwargs):
        for image in self.images.all():
            image.delete()
        for attachment in self.attachments.all():
            attachment.delete()
        super().delete(*args, **kwargs)


class SoftDeletableMixin:
    """
    Mixin for models that support soft-delete in collaborative mode.

    Subclasses must implement `_get_file_field()` returning the file field instance
    (e.g., self.image or self.file).

    Used by: ContentImage, ContentAttachment
    """

    def _get_file_field(self):
        raise NotImplementedError("Subclasses must implement _get_file_field()")

    def delete(self, *args, **kwargs):
        # In collaborative mode, soft-delete instead of hard delete
        if getattr(settings, 'COLLABORATIVE_MODE', False):
            self.is_deleted = True
            self.deleted_at = timezone.now()
            # deleted_by is set by the view
            self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
            return

        # Hard delete: remove file from disk
        file_field = self._get_file_field()
        if file_field and os.path.isfile(file_field.path):
            os.remove(file_field.path)
        super().delete(*args, **kwargs)

    def hard_delete(self, *args, **kwargs):
        """Permanently delete the object and its file."""
        file_field = self._get_file_field()
        if file_field and os.path.isfile(file_field.path):
            os.remove(file_field.path)
        super().delete(*args, **kwargs)

    def restore(self):
        """Restore a soft-deleted object."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
