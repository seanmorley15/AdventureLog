"""Copying a collection and what belongs to it."""

from django.core.files.base import ContentFile
from django.db import transaction

from adventures.models import (
    Checklist, ChecklistItem, Collection, CollectionItineraryDay, CollectionItineraryItem,
    ContentAttachment, ContentImage, Lodging, Note, Transportation,
)


def _read_file(field):
    """The bytes of a stored file, closing it afterwards."""
    try:
        field.open('rb')
        return field.read()
    finally:
        try:
            field.close()
        except Exception:
            pass


def _copy_image(image, user, target):
    """A new photo of ``target`` from an existing one: the file is copied, an Immich photo is referenced."""
    if image.image:
        file_name = (image.image.name or '').split('/')[-1] or 'image.webp'
        copy = ContentImage(
            user=user,
            image=ContentFile(_read_file(image.image), name=file_name),
            immich_id=None,
            is_primary=image.is_primary,
        )
    else:
        copy = ContentImage(user=user, immich_id=image.immich_id, is_primary=image.is_primary)
    copy.content_object = target
    copy.save()
    return copy


def _copy_media(source, target, user):
    """Photos and attachments of one record, for another."""
    for image in source.images.all():
        _copy_image(image, user, target)

    for attachment in source.attachments.all():
        file_name = (attachment.file.name or '').split('/')[-1] or 'attachment'
        copy = ContentAttachment(
            user=user,
            file=ContentFile(_read_file(attachment.file), name=file_name),
            name=attachment.name,
        )
        copy.content_object = target
        copy.save()


def _copy_records(original, copy, user):
    """Transport, notes, lodging and checklists. Returns ``{original id: copy id}`` for relinking placements."""
    id_map = {}

    for item in Transportation.objects.filter(collection=original):
        new_item = Transportation.objects.create(
            user=user, collection=copy, type=item.type, name=item.name, description=item.description,
            rating=item.rating, price=item.price, link=item.link, date=item.date, end_date=item.end_date,
            start_timezone=item.start_timezone, end_timezone=item.end_timezone,
            flight_number=item.flight_number, from_location=item.from_location, origin=item.origin,
            destination=item.destination, start_code=item.start_code, end_code=item.end_code,
            to_location=item.to_location, is_public=item.is_public,
        )
        id_map[item.id] = new_item.id
        _copy_media(item, new_item, user)

    for item in Note.objects.filter(collection=original):
        new_item = Note.objects.create(
            user=user, collection=copy, name=item.name, content=item.content, links=item.links,
            date=item.date, is_public=item.is_public, is_private=item.is_private,
        )
        id_map[item.id] = new_item.id
        _copy_media(item, new_item, user)

    for item in Lodging.objects.filter(collection=original):
        new_item = Lodging.objects.create(
            user=user, collection=copy, name=item.name, type=item.type, description=item.description,
            rating=item.rating, link=item.link, check_in=item.check_in, check_out=item.check_out,
            timezone=item.timezone, reservation_number=item.reservation_number, price=item.price,
            coordinates=item.coordinates, location=item.location, is_public=item.is_public,
        )
        id_map[item.id] = new_item.id
        _copy_media(item, new_item, user)

    for checklist in Checklist.objects.filter(collection=original):
        new_checklist = Checklist.objects.create(
            user=user, collection=copy, name=checklist.name, date=checklist.date, is_public=checklist.is_public,
        )
        id_map[checklist.id] = new_checklist.id
        for entry in checklist.checklistitem_set.all():
            ChecklistItem.objects.create(
                user=user, checklist=new_checklist, name=entry.name,
                is_checked=entry.is_checked, is_private=entry.is_private,
            )

    return id_map


def _copy_day_plan(original, copy, id_map):
    """Days and placements. Logged visits stay with the original."""
    days = {}
    for day in CollectionItineraryDay.objects.filter(collection=original):
        days[day.id] = CollectionItineraryDay.objects.create(
            collection=copy, index=day.index, date=day.date, name=day.name, description=day.description,
        )

    for item in CollectionItineraryItem.objects.filter(collection=original):
        CollectionItineraryItem.objects.create(
            collection=copy,
            content_type=item.content_type,
            # A copied record is placed in the copy; a linked place is shared with the original.
            object_id=id_map.get(item.object_id, item.object_id),
            day=days.get(item.day_id),
            date=item.date,
            is_global=item.is_global,
            order=item.order,
            span_end_index=item.span_end_index,
            is_optional=item.is_optional,
            start_time=item.start_time,
            end_time=item.end_time,
            timezone=item.timezone,
        )


@transaction.atomic
def duplicate_collection(original, user):
    """
    Copy a collection as a new private one named "Copy of ...".

    Places are linked to the copy, not cloned. Transport, notes, checklists and lodging are
    copied with their photos and attachments, and the day plan is rebuilt over the copies.
    Sharing, guest links and comments are left behind.
    """
    copy = Collection.objects.create(
        user=user,
        name=f'Copy of {original.name}',
        description=original.description,
        link=original.link,
        is_public=False,
        is_archived=False,
        start_date=original.start_date,
        end_date=original.end_date,
        type=original.type,
        timezone=original.timezone,
    )

    linked_locations = list(original.locations.all())
    if linked_locations:
        copy.locations.set(linked_locations)

    # The cover is copied so it belongs to the new collection and its permissions.
    if original.primary_image:
        copy.primary_image = _copy_image(original.primary_image, user, copy)
        copy.save(update_fields=['primary_image'])

    _copy_day_plan(original, copy, _copy_records(original, copy, user))
    return copy
