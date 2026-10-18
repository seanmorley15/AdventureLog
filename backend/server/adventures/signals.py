from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from adventures.models import Collection


@receiver(m2m_changed, sender=Collection.shared_with.through)
def sync_collection_members(sender, instance, action, pk_set=None, **kwargs):
    """
    Keep one CollectionMember role row per shared_with user.

    Linking a location to a collection no longer changes ``location.is_public``,
    and publishing a collection no longer changes its children.
    """
    if not isinstance(instance, Collection):
        return
    from adventures.models import CollectionMember

    if action == 'post_add' and pk_set:
        CollectionMember.objects.bulk_create(
            [CollectionMember(collection=instance, user_id=pk) for pk in pk_set],
            ignore_conflicts=True,
        )
    elif action == 'post_remove' and pk_set:
        CollectionMember.objects.filter(collection=instance, user_id__in=pk_set).delete()
    elif action == 'post_clear':
        CollectionMember.objects.filter(collection=instance).delete()


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
