"""Copying a place."""

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import transaction

from adventures.models import Activity, Category, Location, Visit
from adventures.services.images.metadata import create_content_image


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


def _copy_photo(photo, user, location_type, location):
    """Copy one photo onto ``location``: a stored file becomes its own file, an Immich photo is referenced."""
    common = dict(
        user=user,
        content_type=location_type,
        object_id=str(location.id),
        is_primary=photo.is_primary,
        explicit_source=photo.source,
        source_url=photo.source_url,
        coordinates=photo.coordinates,
    )
    if photo.image:
        content = _read_file(photo.image)
        file_name = (photo.image.name or '').split('/')[-1] or 'image.webp'
        create_content_image(image_file=ContentFile(content, name=file_name), file_bytes=content, **common)
    else:
        create_content_image(immich_id=photo.immich_id, **common)


@transaction.atomic
def copy_location(original, user, collection=None, name=None):
    """
    Copy a place for ``user`` as a private place, named ``name`` or "Copy of ..." by default.

    Everything about the place comes along except its collections, visits and attachments;
    photos are copied as independent files. The user's own category of the same name is
    reused, or created from the original's. With ``collection`` the copy is linked to that
    collection alone, instead of inheriting the original's.
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


# Links an activity copy does not keep: its parent is the new visit, and a trail, a trip day or
# the day activity it was promoted from belong to someone else's records.
_ACTIVITY_SKIP = {'id', 'user', 'visit', 'day', 'collection', 'trail', 'promoted_activity', 'gpx_file'}


def _copy_activity(activity, user, visit):
    """Copy one activity onto ``visit`` for ``user``, with its own copy of the track and of the user's photos of it."""
    copy = Activity(
        user=user,
        visit=visit,
        **{
            field.attname: getattr(activity, field.attname)
            for field in Activity._meta.concrete_fields
            if field.name not in _ACTIVITY_SKIP
        },
    )
    if activity.gpx_file:
        file_name = (activity.gpx_file.name or '').split('/')[-1] or 'track.gpx'
        copy.gpx_file = ContentFile(_read_file(activity.gpx_file), name=file_name)
    copy.save()
    activity_type = ContentType.objects.get_for_model(Activity)
    for photo in activity.images.filter(user=user):
        _copy_photo(photo, user, activity_type, copy)
    return copy


@transaction.atomic
def copy_visit_uploads(visit, target, user):
    """
    Copy what ``user`` added to ``visit`` onto ``target``: their photos, attachments and
    activities (with tracks and their photos of them), each with its own files. Things other
    people added are left out, and ``visit`` is not changed.
    """
    from adventures.services.collections.duplicate import copy_attachment

    visit_type = ContentType.objects.get_for_model(Visit)
    for photo in visit.images.filter(user=user):
        _copy_photo(photo, user, visit_type, target)
    for attachment in visit.attachments.filter(user=user):
        copy_attachment(attachment, user, target)
    for activity in visit.activities.filter(user=user):
        _copy_activity(activity, user, target)
