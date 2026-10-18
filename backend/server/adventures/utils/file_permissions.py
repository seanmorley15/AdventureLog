from adventures.models import Activity, Collection, ContentAttachment, ContentImage, Visit
from adventures.utils.audience import is_member
from adventures.utils.day_files import activity_collection, image_day_collection
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


def _authenticated(user):
    return user is not None and getattr(user, 'is_authenticated', False)


def _collection_allows(collection, user, request=None, story_group=None):
    """
    Members and guest links read every file. A reader of a public or unlisted
    story reads photos, and reads attachments or GPX only when that group is on.
    Unlisted media has no secret in its URL; the file names are random.
    """
    if collection is None:
        return False
    if _authenticated(user) and is_member(user, collection):
        return True
    if request is not None and is_member(request, collection):
        return True
    if collection.visibility in (Collection.Visibility.PUBLIC, Collection.Visibility.UNLISTED):
        return story_group is None or collection.story_group(story_group)
    return False


def _check_content_object_permission(content_object, user, request=None, story_group=None):
    """Check if the requester may read a file attached to ``content_object``."""
    # handle differently when content_object is a Visit, get the location instead
    if isinstance(content_object, Visit):
        if content_object.location:
            content_object = content_object.location

    # Check if user owns the content object
    if _authenticated(user) and getattr(content_object, 'user', None) == user:
        return True

    # A location's own public flag publishes its files, as before.
    if hasattr(content_object, 'collections'):
        if getattr(content_object, 'is_public', False):
            return True
        return any(
            _collection_allows(collection, user, request, story_group)
            for collection in content_object.collections.all()
        )

    # Lodging, transport, and notes in a collection follow that collection, not their own flag.
    collection = getattr(content_object, 'collection', None)
    if collection is not None:
        return _collection_allows(collection, user, request, story_group)
    return bool(getattr(content_object, 'is_public', False))


def checkFilePermission(fileId, user, mediaType, request=None):
    if mediaType not in PROTECTED_MEDIA_PATHS:
        return False
    if mediaType == 'images/':
        image_path = f"images/{fileId}"
        # Use filter() instead of get() to handle multiple ContentImage entries
        # pointing to the same file (e.g. after location duplication)
        content_images = ContentImage.objects.filter(image=image_path)
        if not content_images.exists():
            return False
        # Grant access if ANY associated content object permits it.
        for content_image in content_images:
            day_collection = image_day_collection(content_image)
            if day_collection is not None:
                if _collection_allows(day_collection, user, request):
                    return True
                continue
            content_object = content_image.content_object
            if content_object and _check_content_object_permission(content_object, user, request):
                return True
        return False
    elif mediaType == 'attachments/':
        try:
            attachment_path = f"attachments/{fileId}"
            content_attachment = ContentAttachment.objects.get(file=attachment_path)
            content_object = content_attachment.content_object
            if not content_object:
                return False
            return _check_content_object_permission(content_object, user, request, story_group='attachments')
        except ContentAttachment.DoesNotExist:
            return False
    elif mediaType == 'activities/':
        activity_path = f"activities/{fileId}"
        activities = Activity.objects.filter(gpx_file=activity_path)
        if not activities.exists():
            return False
        for activity in activities:
            if activity.visit_id:
                if activity.visit and _check_content_object_permission(activity.visit, user, request, story_group='gpx'):
                    return True
                continue
            if _collection_allows(activity_collection(activity), user, request, story_group='gpx'):
                return True
        return False
    return False


def is_day_owned_media(file_id, media_type):
    """
    True when every row for this file is a day-owned activity or photo.

    A denied request for that file is 404, including for a public collection.
    A location GPX that shares nothing with a day file keeps today's response.
    """
    if media_type == 'activities/':
        activities = list(Activity.objects.filter(gpx_file=f'activities/{file_id}'))
        return bool(activities) and all(activity.visit_id is None for activity in activities)
    if media_type == 'images/':
        images = list(ContentImage.objects.filter(image=f'images/{file_id}'))
        return bool(images) and all(image_day_collection(image) is not None for image in images)
    return False
