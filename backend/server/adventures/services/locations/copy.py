"""Copying a place."""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from adventures.models import Activity, Category, ContentAttachment, ContentImage, Location, Visit


def _photo_copy(photo, user, content_type, target):
    """
    An unsaved copy of one photo onto ``target`` for ``user``. A stored file is shared, not copied:
    the copy keeps the same storage name, and the file stays until the last row using it is
    deleted (``adventures.signals``). Nothing is read, so a missing file is carried over as it is.

    An Immich photo is shown through its owner's Immich account, so it is copied only for that
    owner; anyone else gets nothing for it (returns None).

    The copies are inserted in bulk, so ``save()`` and its ``full_clean`` don't run. A photo is
    already valid, and the copy keeps exactly one of its file and its Immich id.
    """
    if not photo.image and photo.user_id != user.pk:
        return None
    return ContentImage(
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


def _copy_photos(photos, user, content_type, target_for):
    """Insert copies of ``photos`` in one query; ``target_for(photo)`` names where each one goes."""
    copies = [_photo_copy(photo, user, content_type, target_for(photo)) for photo in photos]
    return ContentImage.objects.bulk_create([copy for copy in copies if copy is not None])


def shared_file_names(original):
    """The stored files a copy of ``original`` (``copy_location``) would share: its photos' files."""
    return list(original.images.exclude(image__isnull=True).exclude(image='').values_list('image', flat=True))


@transaction.atomic
def copy_location(original, user, collection=None, name=None):
    """
    Copy a place for ``user`` as a private place, named ``name`` or "Copy of ..." by default.

    Everything about the place comes along except its collections, visits, attachments and
    trails. Photos share the original's stored files (``_photo_copy``): deleting either place
    never removes a file the other still shows. Someone else's copy leaves out Immich photos,
    which only the original owner's Immich account can show (if the cover was one, another photo
    becomes the cover). The user's own category of the same name is reused, or created from the
    original's. With ``collection`` the copy is linked to that collection alone, instead of
    inheriting the original's.
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
    copies = [c for c in (_photo_copy(photo, user, location_type, copy) for photo in photos) if c is not None]
    # Someone else's copy leaves out the owner's Immich photos. When the cover was one of them,
    # the first photo that came along becomes the cover, so the copy still has one.
    if copies and not any(c.is_primary for c in copies) and any(photo.is_primary for photo in photos):
        copies[0].is_primary = True
    ContentImage.objects.bulk_create(copies)
    return copy


# Links an activity copy does not keep: its parent is the new visit, and a trail (a Wanderer one
# resolves through its owner's integration), a trip day or the day activity it was promoted from
# belong to someone else's records. The track is shared, not copied (``_activity_copy``).
_ACTIVITY_SKIP = {'id', 'user', 'visit', 'day', 'collection', 'trail', 'promoted_activity', 'gpx_file'}


def _activity_copy(activity, user, visit):
    """
    An unsaved copy of one activity onto ``visit`` for ``user``. The track file is shared with the
    original (see ``_photo_copy``), so nothing is read or written.
    """
    return Activity(
        user=user,
        visit=visit,
        gpx_file=activity.gpx_file.name or None,
        **{
            field.attname: getattr(activity, field.attname)
            for field in Activity._meta.concrete_fields
            if field.name not in _ACTIVITY_SKIP
        },
    )


@transaction.atomic
def copy_visit_uploads(visit, target, user):
    """
    Copy what ``user`` added to ``visit`` onto ``target``: their photos, attachments and
    activities (with tracks and their photos of them), sharing the stored files. Things other
    people added are left out, and ``visit`` is not changed. Nothing is read, so a missing file
    never blocks a leave: it is carried over as it is. Each kind of row is inserted in one query,
    however many there are. Bulk inserts skip ``ContentImage.save``'s ``full_clean`` (see
    ``_photo_copy``); none of these models has a post_save receiver.
    """
    visit_type = ContentType.objects.get_for_model(Visit)
    _copy_photos(visit.images.filter(user=user), user, visit_type, lambda photo: target)
    ContentAttachment.objects.bulk_create([
        ContentAttachment(
            user=user, content_type=visit_type, object_id=target.pk,
            file=attachment.file.name, name=attachment.name,
        )
        for attachment in visit.attachments.filter(user=user)
    ])

    activities = list(visit.activities.filter(user=user))
    copies = {activity.pk: _activity_copy(activity, user, target) for activity in activities}
    Activity.objects.bulk_create(copies.values())
    activity_type = ContentType.objects.get_for_model(Activity)
    photos = ContentImage.objects.filter(content_type=activity_type, object_id__in=list(copies), user=user)
    _copy_photos(photos, user, activity_type, lambda photo: copies[photo.object_id])
