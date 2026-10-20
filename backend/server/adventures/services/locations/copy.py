"""Copying a place."""

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import transaction

from adventures.models import Category, Location
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
def copy_location(original, user, collection=None):
    """
    Copy a place for ``user`` as a private "Copy of ..." place.

    Everything about the place comes along except its collections, visits and attachments;
    photos are copied as independent files. The user's own category of the same name is
    reused, or created from the original's. With ``collection`` the copy is linked to that
    collection alone, instead of inheriting the original's.
    """
    copy = Location(
        user=user,
        name=f'Copy of {original.name}',
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
