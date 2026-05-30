from django.conf import settings
from django.core.files.storage import default_storage
from adventures.models import ContentAttachment, ContentImage


def get_media_storage_limit_bytes():
    limit = getattr(settings, 'MEDIA_STORAGE_LIMIT_BYTES', 0) or 0
    return limit if limit > 0 else None


def get_uploaded_file_size(file_obj):
    if not file_obj:
        return 0
    size = getattr(file_obj, 'size', None)
    if size is None:
        try:
            size = len(file_obj)
        except TypeError:
            size = 0
    return size or 0


def _sum_storage_sizes(names):
    total = 0
    for name in names:
        if not name:
            continue
        try:
            total += default_storage.size(name)
        except (OSError, ValueError, FileNotFoundError):
            continue
    return total


def get_user_media_usage(user, exclude_names=None):
    exclude_names = set(filter(None, exclude_names or []))

    image_names = set(
        ContentImage.objects.filter(user=user)
        .exclude(image__isnull=True)
        .exclude(image='')
        .values_list('image', flat=True)
    )
    attachment_names = set(
        ContentAttachment.objects.filter(user=user)
        .exclude(file__isnull=True)
        .exclude(file='')
        .values_list('file', flat=True)
    )
    profile_names = set()
    if user.profile_pic and user.profile_pic.name:
        profile_names.add(user.profile_pic.name)

    image_names -= exclude_names
    attachment_names -= exclude_names
    profile_names -= exclude_names

    images_bytes = _sum_storage_sizes(image_names)
    attachments_bytes = _sum_storage_sizes(attachment_names)
    profile_pics_bytes = _sum_storage_sizes(profile_names)

    return {
        "total_bytes": images_bytes + attachments_bytes + profile_pics_bytes,
        "images_bytes": images_bytes,
        "attachments_bytes": attachments_bytes,
        "profile_pics_bytes": profile_pics_bytes,
        "images_files": len(image_names),
        "attachments_files": len(attachment_names),
        "profile_pics_files": len(profile_names),
    }


def enforce_media_storage_limit(user, incoming_bytes, exclude_names=None):
    limit = get_media_storage_limit_bytes()
    if not limit:
        return True, None

    usage = get_user_media_usage(user, exclude_names=exclude_names)
    projected = usage["total_bytes"] + max(incoming_bytes, 0)

    if projected > limit:
        return False, {
            "limit_bytes": limit,
            "current_bytes": usage["total_bytes"],
            "incoming_bytes": incoming_bytes,
        }

    return True, None
