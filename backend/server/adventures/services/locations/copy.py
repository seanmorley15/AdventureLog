"""Copying a place."""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from adventures.models import Activity, Category, ContentAttachment, ContentImage, Location, Visit


def _copy_photo(photo, user, content_type, target):
    """
    Copy one photo onto ``target`` for ``user``. A stored file is shared, not copied: the copy
    keeps the same storage name, and the file stays until the last row using it is deleted
    (``adventures.signals``). Nothing is read, so a missing file is carried over as it is.

    An Immich photo is shown through its owner's Immich account, so it is copied only for that
    owner; anyone else gets nothing for it (returns None).
    """
    if not photo.image and photo.user_id != user.pk:
        return None
    copy = ContentImage(
        user=user,
        content_type=content_type,
        object_id=target.pk,
        image=photo.image.name or None,
        immich_id=None if photo.image else photo.immich_id,
        is_primary=photo.is_primary,
        source=photo.source,
        source_url=photo.source_url,
        coordinates=photo.coordinates,
    )
    copy.save()
    return copy


def _copy_attachment(attachment, user, target):
    """Copy one attachment onto ``target`` for ``user``, sharing its stored file (see ``_copy_photo``)."""
    copy = ContentAttachment(user=user, file=attachment.file.name, name=attachment.name)
    copy.content_object = target
    copy.save()
    return copy


@transaction.atomic
def copy_location(original, user, collection=None, name=None):
    """
    Copy a place for ``user`` as a private place, named ``name`` or "Copy of ..." by default.

    Everything about the place comes along except its collections, visits, attachments and
    trails. Photos share the original's stored files (``_copy_photo``): deleting either place
    never removes a file the other still shows. Someone else's copy leaves out Immich photos,
    which only the original owner's Immich account can show. The user's own category of the
    same name is reused, or created from the original's. With ``collection`` the copy is
    linked to that collection alone, instead of inheriting the original's.
    """
    copy = Location(
        user=user,
        name=name if name is not None else f'Copy of {original.name}',
        description=original.description,
        rating=original.rating,
        link=original.link,
        location=original.location,
        tags=list(original.tags) if original.tags else None,
        is_public=False,
        coordinates=original.coordinates,
        city=original.city,
        region=original.region,
        country=original.country,
        price=original.price,
        price_currency=original.price_currency,
    )

    if original.category:
        copy.category, _ = Category.objects.get_or_create(
            user=user,
            name=original.category.name,
            defaults={
                'display_name': original.category.display_name,
                'icon': original.category.icon,
            },
        )

    # Snapshot the photos before the copy exists, so it can never copy itself.
    photos = list(original.images.all())
    copy.save()

    if collection is not None:
        copy.collections.set([collection])

    location_type = ContentType.objects.get_for_model(Location)
    for photo in photos:
        _copy_photo(photo, user, location_type, copy)
    return copy


# Links an activity copy does not keep: its parent is the new visit, and a trail (a Wanderer one
# resolves through its owner's integration), a trip day or the day activity it was promoted from
# belong to someone else's records. The track is shared, not copied (``_copy_activity``).
_ACTIVITY_SKIP = {'id', 'user', 'visit', 'day', 'collection', 'trail', 'promoted_activity', 'gpx_file'}


def _copy_activity(activity, user, visit):
    """
    Copy one activity onto ``visit`` for ``user``, with the user's photos of it. The track file is
    shared with the original (see ``_copy_photo``), so nothing is read or written.
    """
    copy = Activity(
        user=user,
        visit=visit,
        **{
            field.attname: getattr(activity, field.attname)
            for field in Activity._meta.concrete_fields
            if field.name not in _ACTIVITY_SKIP
        },
    )
    copy.gpx_file = activity.gpx_file.name or None
    copy.save()
    activity_type = ContentType.objects.get_for_model(Activity)
    for photo in activity.images.filter(user=user):
        _copy_photo(photo, user, activity_type, copy)
    return copy


@transaction.atomic
def copy_visit_uploads(visit, target, user):
    """
    Copy what ``user`` added to ``visit`` onto ``target``: their photos, attachments and
    activities (with tracks and their photos of them), sharing the stored files. Things other
    people added are left out, and ``visit`` is not changed. Nothing is read, so a missing file
    never blocks a leave: it is carried over as it is.
    """
    visit_type = ContentType.objects.get_for_model(Visit)
    for photo in visit.images.filter(user=user):
        _copy_photo(photo, user, visit_type, target)
    for attachment in visit.attachments.filter(user=user):
        _copy_attachment(attachment, user, target)
    for activity in visit.activities.filter(user=user):
        _copy_activity(activity, user, target)
