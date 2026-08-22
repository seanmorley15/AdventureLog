from adventures.models import Activity, ContentAttachment, ContentImage, Visit
import posixpath

PUBLIC_MEDIA_PATHS = ('profile-pics/', 'achievements/', 'flags/')
PROTECTED_MEDIA_PATHS = ('images/', 'attachments/', 'activities/')


def normalize_media_request_path(path):
    if not path or '\x00' in path:
        return None

    normalized = posixpath.normpath(path)
    if normalized in ('.', '..') or normalized.startswith('../') or normalized.startswith('/'):
        return None

    return normalized


def is_public_media_path(path):
    return path.startswith(PUBLIC_MEDIA_PATHS)


def is_protected_media_path(path):
    return path.startswith(PROTECTED_MEDIA_PATHS)


def _check_content_object_permission(content_object, user):
    """Check if user has permission to access a content object."""
    # handle differently when content_object is a Visit, get the location instead
    if isinstance(content_object, Visit):
        if content_object.location:
            content_object = content_object.location

    # Check if content object is public
    if hasattr(content_object, 'is_public') and content_object.is_public:
        return True

    # Check if user owns the content object
    if hasattr(content_object, 'user') and content_object.user == user:
        return True

    # Check collection-based permissions
    if hasattr(content_object, 'collections') and content_object.collections.exists():
        for collection in content_object.collections.all():
            if collection.user == user or collection.shared_with.filter(id=user.id).exists():
                return True
        return False
    elif hasattr(content_object, 'collection') and content_object.collection:
        if content_object.collection.user == user or content_object.collection.shared_with.filter(id=user.id).exists():
            return True
        return False
    else:
        return False

def checkFilePermission(fileId, user, mediaType):
    if mediaType not in PROTECTED_MEDIA_PATHS:
        return False
    if mediaType == 'images/':
        image_path = f"images/{fileId}"
        # Use filter() instead of get() to handle multiple ContentImage entries
        # pointing to the same file (e.g. after location duplication)
        content_images = ContentImage.objects.filter(image=image_path)
        if not content_images.exists():
            return False
        # Grant access if ANY associated content object permits it
        for content_image in content_images:
            content_object = content_image.content_object
            if content_object and _check_content_object_permission(content_object, user):
                return True
        return False
    elif mediaType == 'attachments/':
        try:
            attachment_path = f"attachments/{fileId}"
            content_attachment = ContentAttachment.objects.get(file=attachment_path)
            content_object = content_attachment.content_object
            return _check_content_object_permission(content_object, user) if content_object else False
        except ContentAttachment.DoesNotExist:
            return False
    elif mediaType == 'activities/':
        activity_path = f"activities/{fileId}"
        activities = Activity.objects.filter(gpx_file=activity_path)
        if not activities.exists():
            return False
        for activity in activities:
            if activity.visit and _check_content_object_permission(activity.visit, user):
                return True
        return False
    return False
