from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from threading import local

from adventures.models import Location

# Thread-local storage for current user (used by audit logging)
_thread_locals = local()


def set_current_user(user):
    """Called by middleware to set the current user for audit logging."""
    _thread_locals.user = user


def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_locals, 'user', None)


@receiver(m2m_changed, sender=Location.collections.through)
def update_adventure_publicity(sender, instance, action, **kwargs):
    """
    Signal handler to update adventure publicity when collections are added/removed
    This function checks if the adventure's collections contain any public collection.
    """
    if not isinstance(instance, Location):
        return
    # Only process when collections are added or removed
    if action in ('post_add', 'post_remove', 'post_clear'):
        collections = instance.collections.all()
        
        if collections.exists():
            # If any collection is public, make the adventure public
            has_public_collection = collections.filter(is_public=True).exists()
            
            if has_public_collection and not instance.is_public:
                instance.is_public = True
                instance.save(update_fields=['is_public'])
            elif not has_public_collection and instance.is_public:
                instance.is_public = False
                instance.save(update_fields=['is_public'])


@receiver(post_delete)
def _remove_collection_itinerary_items_on_object_delete(sender, instance, **kwargs):
    """
    When any model instance is deleted, remove any CollectionItineraryItem that
    refers to it via the GenericForeignKey (matches by ContentType and object_id).

    This ensures that if a referenced item (e.g. a `Location`, `Visit`, `Transportation`,
    `Note`, etc.) is deleted, the itinerary entry that pointed to it is also removed.
    """
    # Avoid acting when a CollectionItineraryItem itself is deleted
    # to prevent needless extra queries.
    if sender.__name__ == 'CollectionItineraryItem':
        return

    # Resolve the content type for the model that was deleted
    try:
        ct = ContentType.objects.get_for_model(sender)
    except Exception:
        return

    # Import here to avoid circular import problems at module import time
    from adventures.models import CollectionItineraryItem

    # Try matching the primary key in its native form first, then as a string.
    # CollectionItineraryItem.object_id is a UUIDField in the model, but some
    # senders might have different PK representations; handle both safely.
    pk = instance.pk
    deleted = False
    try:
        qs = CollectionItineraryItem.objects.filter(content_type=ct, object_id=pk)
        if qs.exists():
            qs.delete()
            deleted = True
    except Exception:
        pass

    if not deleted:
        try:
            CollectionItineraryItem.objects.filter(content_type=ct, object_id=str(pk)).delete()
        except Exception:
            # If deletion fails for any reason, do nothing; we don't want to
            # raise errors during another model's delete.
            pass


# ---------------------------------------------------------------------------
# Audit Logging for Collaborative Mode
# ---------------------------------------------------------------------------

def _get_auditable_models():
    """Returns list of models that should be audited in collaborative mode."""
    from adventures.models import (
        Location, Collection, Category, Visit, ContentImage, ContentAttachment,
        Note, Transportation, Lodging
    )
    return [Location, Collection, Category, Visit, ContentImage, ContentAttachment, Note, Transportation, Lodging]


@receiver(pre_save)
def track_changes_before_save(sender, instance, **kwargs):
    """Store old values before save for comparison in audit log."""
    if not getattr(settings, 'COLLABORATIVE_MODE', False):
        return

    auditable_models = _get_auditable_models()
    if sender not in auditable_models:
        return

    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_values = {
                field.name: getattr(old_instance, field.name)
                for field in sender._meta.fields
            }
        except sender.DoesNotExist:
            instance._old_values = {}


@receiver(post_save)
def log_save_to_audit(sender, instance, created, **kwargs):
    """Log create/update actions to AuditLog in collaborative mode."""
    if not getattr(settings, 'COLLABORATIVE_MODE', False):
        return

    auditable_models = _get_auditable_models()
    if sender not in auditable_models:
        return

    from adventures.models import AuditLog

    user = get_current_user()
    action = 'create' if created else 'update'

    changes = {}
    if not created and hasattr(instance, '_old_values'):
        for field, old_value in instance._old_values.items():
            new_value = getattr(instance, field)
            if old_value != new_value:
                changes[field] = {'old': str(old_value), 'new': str(new_value)}

    # Only log updates if there were actual changes
    if action == 'update' and not changes:
        return

    AuditLog.objects.create(
        user=user,
        action=action,
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.pk,
        object_repr=str(instance)[:200],
        changes=changes
    )


@receiver(post_delete)
def log_delete_to_audit(sender, instance, **kwargs):
    """Log delete actions to AuditLog in collaborative mode."""
    if not getattr(settings, 'COLLABORATIVE_MODE', False):
        return

    auditable_models = _get_auditable_models()
    if sender not in auditable_models:
        return

    from adventures.models import AuditLog

    AuditLog.objects.create(
        user=get_current_user(),
        action='delete',
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.pk,
        object_repr=str(instance)[:200],
        changes={}
    )
