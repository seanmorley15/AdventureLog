"""Day-owned trails, activities, and photos.

A place activity keeps its visit. A day activity has no visit and a day parent.
Ideas is the third parent: the collection, with no day and no visit. The same
split applies to trails (location, day, or the collection). Photos use the
ContentImage generic key and may parent to the day, the day's activity, the
day's trail, or the collection while they sit in Ideas.

These rows are readable by the collection owner and ``shared_with`` only.
``is_public`` does not publish them.
"""

import os

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db.models import Q

from adventures.models import Activity, Collection, CollectionItineraryDay, ContentImage, Trail

COPY_FIELDS = (
    'name',
    'sport_type',
    'distance',
    'moving_time',
    'elapsed_time',
    'rest_time',
    'elevation_gain',
    'elevation_loss',
    'elev_high',
    'elev_low',
    'start_date',
    'start_date_local',
    'timezone',
    'average_speed',
    'max_speed',
    'average_cadence',
    'calories',
    'start_point',
    'end_point',
    'trail',
)


def activity_collection(activity):
    """The collection that owns a day or Ideas activity. None for a place activity."""
    if activity.visit_id:
        return None
    if activity.day_id:
        return activity.day.collection
    return activity.collection


def trail_collection(trail):
    """The collection that owns a day or Ideas trail. None for a place trail."""
    if trail.location_id:
        return None
    if trail.day_id:
        return trail.day.collection
    return trail.collection


def image_day_collection(image):
    """
    The collection for a day-owned photo.

    None when the photo belongs to a place, a visit, or anything else that
    still follows the location publicity rules.
    """
    parent = image.content_object
    if parent is None:
        return None
    if isinstance(parent, CollectionItineraryDay):
        return parent.collection
    if isinstance(parent, Collection):
        return parent
    if isinstance(parent, Activity):
        return activity_collection(parent)
    if isinstance(parent, Trail):
        return trail_collection(parent)
    return None


def _content_type(model):
    return ContentType.objects.get_for_model(model)


def day_file_activities(collection):
    return (
        Activity.objects.filter(Q(day__collection=collection) | Q(collection=collection))
        .select_related('day', 'trail', 'promoted_activity', 'promoted_activity__visit')
        .distinct()
        .order_by('day__index', 'name', 'id')
    )


def day_file_trails(collection):
    return (
        Trail.objects.filter(Q(day__collection=collection) | Q(collection=collection))
        .select_related('day')
        .distinct()
        .order_by('day__index', 'name', 'id')
    )


def day_file_images(collection):
    """Photos parented to a day, a day file, or the collection (Ideas)."""
    activities = Activity.objects.filter(Q(day__collection=collection) | Q(collection=collection))
    trails = Trail.objects.filter(Q(day__collection=collection) | Q(collection=collection))
    days = CollectionItineraryDay.objects.filter(collection=collection)
    return ContentImage.objects.filter(
        Q(content_type=_content_type(CollectionItineraryDay), object_id__in=days.values('id'))
        | Q(content_type=_content_type(Activity), object_id__in=activities.values('id'))
        | Q(content_type=_content_type(Trail), object_id__in=trails.values('id'))
        | Q(content_type=_content_type(Collection), object_id=collection.id)
    ).distinct().order_by('content_type_id', 'id')


def image_belongs_to_collection(image, collection):
    """True when a cover may be this collection's day photo."""
    if ContentImage.objects.filter(id=image.id, location__collections=collection).exists():
        return True
    if ContentImage.objects.filter(id=image.id, visit__location__collections=collection).exists():
        return True
    parent_collection = image_day_collection(image)
    return parent_collection is not None and parent_collection.id == collection.id


def _reparent_images(images, target):
    content_type = _content_type(type(target))
    for image in images:
        image.content_type = content_type
        image.object_id = target.pk
        image.save(update_fields=['content_type', 'object_id'])


def blocking_day_files(day):
    """
    Day-owned records that do not continue onto a later day.

    A trail that spans past this day moves with the span and is not listed here.
    """
    activities = list(Activity.objects.filter(day=day))
    trails = [
        trail
        for trail in Trail.objects.filter(day=day)
        if not (trail.span_end_index and trail.span_end_index > day.index)
    ]
    photos = list(
        ContentImage.objects.filter(
            content_type=_content_type(CollectionItineraryDay),
            object_id=day.pk,
        )
    )
    return activities, trails, photos


def blocking_file_count(day):
    activities, trails, photos = blocking_day_files(day)
    return len(activities) + len(trails) + len(photos)


def move_blocking_files(day, destination, target_day, collection):
    """Move this day's own files onto another day, or into Ideas."""
    activities, trails, photos = blocking_day_files(day)
    activity_ids = [activity.pk for activity in activities]
    trail_ids = [trail.pk for trail in trails]
    if destination == 'day':
        if activity_ids:
            Activity.objects.filter(pk__in=activity_ids).update(day=target_day)
        if trail_ids:
            Trail.objects.filter(pk__in=trail_ids).update(day=target_day, span_end_index=None)
        _reparent_images(photos, target_day)
        return
    if activity_ids:
        Activity.objects.filter(pk__in=activity_ids).update(day=None, collection=collection)
    if trail_ids:
        Trail.objects.filter(pk__in=trail_ids).update(day=None, collection=collection, span_end_index=None)
    _reparent_images(photos, collection)


def extend_trail_spans(collection, position):
    """Inserting a day at ``position`` lengthens spans that cover or follow it."""
    trails = list(
        Trail.objects.filter(day__collection=collection, span_end_index__isnull=False).select_related('day')
    )
    for trail in trails:
        start, end = trail.day.index, trail.span_end_index
        if start < position <= end or position <= start:
            trail.span_end_index = end + 1
    if trails:
        Trail.objects.bulk_update(trails, ['span_end_index'])


def shrink_trail_spans(collection, removed, next_day):
    """
    Deleting day ``removed`` shortens spans.

    A span that starts on the deleted day moves to ``next_day``.
    """
    trails = list(
        Trail.objects.filter(day__collection=collection, span_end_index__isnull=False).select_related('day')
    )
    moved = []
    for trail in trails:
        start, end = trail.day.index, trail.span_end_index
        if start == removed:
            moved.append(trail)
            new_start = removed
        else:
            new_start = start if start < removed else start - 1
        new_end = end - 1 if end >= removed else end
        trail.span_end_index = new_end if new_end > new_start else None
    if trails:
        Trail.objects.bulk_update(trails, ['span_end_index'])
    if moved and next_day is not None:
        Trail.objects.filter(pk__in=[trail.pk for trail in moved]).update(day=next_day)


def retarget_trail_spans(spans, by_pk, day_count):
    """After days are renumbered, keep each trail's length on its new index."""
    for trail, length in spans:
        trail.day = by_pk[trail.day_id]
        trail.span_end_index = min(trail.day.index + length, day_count)
        if trail.span_end_index <= trail.day.index:
            trail.span_end_index = None
    if spans:
        Trail.objects.bulk_update([trail for trail, _length in spans], ['day', 'span_end_index'])


def trail_span_lengths(collection):
    trails = Trail.objects.filter(day__collection=collection, span_end_index__isnull=False).select_related('day')
    return [(trail, trail.span_end_index - trail.day.index) for trail in trails]


def _copy_file(field):
    if not field or not getattr(field, 'name', None):
        return None
    field.open('rb')
    try:
        payload = field.read()
    finally:
        field.close()
    return os.path.basename(field.name), payload


def _duplicate_image(image, target, user):
    clone = ContentImage(
        user=user,
        is_primary=False,
        source=image.source,
        source_url=image.source_url,
        immich_id=image.immich_id,
        coordinates=image.coordinates,
        content_type=_content_type(type(target)),
        object_id=target.pk,
    )
    copied = _copy_file(image.image)
    if copied:
        clone.image.save(copied[0], ContentFile(copied[1]), save=False)
    clone.save()
    return clone


def location_stops_on_day(day):
    """Location placements listed on ``day``, including spans that cover it."""
    from adventures.models import CollectionItineraryItem

    stops = []
    items = CollectionItineraryItem.objects.filter(
        collection=day.collection,
        content_type__model='location',
    ).select_related('day', 'content_type')
    for item in items:
        if item.day_id == day.id:
            stops.append(item)
            continue
        if (
            item.day_id
            and item.span_end_index
            and item.day.index <= day.index <= item.span_end_index
        ):
            stops.append(item)
    return stops


def _stop_name(item):
    obj = item.item
    return getattr(obj, 'name', None) or 'Stop'


def promote_day_activity(activity, placement=None, visit_date=None):
    """
    Copy a day activity's GPX, times, and photos onto one location stop's visit.

    The day activity stays where it is. A second call returns the copy already made.
    One location stop on the day is the default. Several stops need ``placement``.
    """
    from .errors import DayPlanError
    from .visits import log_visited

    if activity.visit_id:
        raise DayPlanError('This activity is already on a visit.')
    if activity.day_id is None:
        raise DayPlanError('Put this activity on a day before logging it.')
    if activity.promoted_activity_id:
        copy = activity.promoted_activity
        return copy.visit, copy, False

    stops = location_stops_on_day(activity.day)
    if placement is None:
        if len(stops) == 1:
            placement = stops[0]
        elif not stops:
            raise DayPlanError(
                'Add a location stop on this day before logging this activity.',
                code='stop_required',
                extra={'stops': []},
            )
        else:
            raise DayPlanError(
                'Choose which stop this visit belongs to.',
                code='stop_required',
                extra={'stops': [{'id': str(stop.pk), 'name': _stop_name(stop)} for stop in stops]},
            )
    else:
        match = next((stop for stop in stops if stop.pk == placement.pk), None)
        if match is None:
            raise DayPlanError('That stop is not on this day.')
        placement = match

    visit, _created = log_visited(placement, visit_date)
    owner = visit.location.user
    copy = Activity(user=owner, visit=visit)
    for field in COPY_FIELDS:
        setattr(copy, field, getattr(activity, field))
    copied = _copy_file(activity.gpx_file)
    if copied:
        copy.gpx_file.save(copied[0], ContentFile(copied[1]), save=False)
    copy.save()
    for image in activity.images.all():
        _duplicate_image(image, copy, owner)
    activity.promoted_activity = copy
    activity.save(update_fields=['promoted_activity'])
    return visit, copy, True


def promote_ready_activities(day, visit_date=None):
    """
    Copy each unlogged day activity when the day has one location stop.

    Several stops are left for the activity's own Log visit button.
    Returns ``(promoted activities, activities that still need a stop)``.
    """
    activities = list(
        Activity.objects.filter(day=day, promoted_activity__isnull=True).select_related('day', 'trail')
    )
    if not activities:
        return [], []
    stops = location_stops_on_day(day)
    if len(stops) != 1:
        return [], activities if stops else []
    promoted = []
    for activity in activities:
        promote_day_activity(activity, placement=stops[0], visit_date=visit_date)
        promoted.append(activity)
    return promoted, []


def serialize_day_files(collection, context=None):
    """Day trails, activities, and photos for the collection payload."""
    from adventures.serializers import ActivitySerializer, ContentImageSerializer, TrailSerializer

    context = context or {}
    images = []
    for image in day_file_images(collection).select_related('content_type'):
        data = ContentImageSerializer(image, context=context).data
        if not data:
            continue
        data['content_type'] = image.content_type.model
        data['object_id'] = str(image.object_id)
        images.append(data)
    return {
        'day_activities': ActivitySerializer(day_file_activities(collection), many=True, context=context).data,
        'day_trails': TrailSerializer(day_file_trails(collection), many=True, context=context).data,
        'day_images': images,
    }


def purge_collection_day_files(collection):
    """Delete day-owned trails, activities, and photos. Locations and their visits stay."""
    activities = list(day_file_activities(collection))
    trails = list(day_file_trails(collection))
    images = list(day_file_images(collection))
    for image in images:
        image.delete()
    # A logged copy lives on the visit and references the day trail. Drop that
    # link before the trail goes away so the visit activity stays with the place.
    if trails:
        Activity.objects.filter(trail__in=trails, visit__isnull=False).update(trail=None)
    if activities:
        Activity.objects.filter(pk__in=[activity.pk for activity in activities]).delete()
    if trails:
        Trail.objects.filter(pk__in=[trail.pk for trail in trails]).delete()
