import logging

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from adventures.models import (
    Activity,
    Checklist,
    Collection,
    CollectionItineraryItem,
    ContentAttachment,
    ContentImage,
    Location,
    Lodging,
    Note,
    Transportation,
    Visit,
)

logger = logging.getLogger(__name__)


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


def _remove_collection_itinerary_items_on_object_delete(sender, instance, **kwargs):
    """
    When something an itinerary item can point at is deleted, remove the items that
    refer to it through the GenericForeignKey (matched by ContentType and object_id).
    """
    CollectionItineraryItem.objects.filter(
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.pk,
    ).delete()


# The records CollectionItineraryItem.item can refer to (see CONTENT_MODELS in the itinerary view).
for _model in (Location, Visit, Lodging, Transportation, Note, Checklist):
    post_delete.connect(
        _remove_collection_itinerary_items_on_object_delete,
        sender=_model,
        dispatch_uid=f'remove_itinerary_items_{_model.__name__}',
    )


def _delete_file_when_unreferenced(model, field_name, file):
    """
    Remove a stored file once no row of ``model`` uses it, after the delete commits.
    Rows can share one file (a duplicated place), so the file stays while any remains.
    """
    if not file or not file.name:
        return
    name, storage = file.name, file.storage

    def delete():
        if model.objects.filter(**{field_name: name}).exists():
            return
        try:
            storage.delete(name)
        except Exception:
            logger.exception('Could not delete stored file %s', name)

    transaction.on_commit(delete)


@receiver(post_delete, sender=ContentImage)
def _delete_image_file(sender, instance, **kwargs):
    _delete_file_when_unreferenced(ContentImage, 'image', instance.image)


@receiver(post_delete, sender=ContentAttachment)
def _delete_attachment_file(sender, instance, **kwargs):
    _delete_file_when_unreferenced(ContentAttachment, 'file', instance.file)


@receiver(post_delete, sender=Activity)
def _delete_activity_gpx_file(sender, instance, **kwargs):
    _delete_file_when_unreferenced(Activity, 'gpx_file', instance.gpx_file)
