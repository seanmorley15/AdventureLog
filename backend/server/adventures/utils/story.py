"""
The published story: what a public reader receives.

Built by whitelisting the member payload, never by deleting from it, so a new
field stays private until it is added here. Each group is off until the owner
turns it on:

- ``place_details``: place descriptions, links, and ratings. This copies them
  into the story only; the place record and its own page stay private.
- ``costs``: prices.
- ``reservations``: reservation and flight numbers, booking links.
- ``attachments``: attachment files.
- ``lodging_address``: lodging address and pin.
- ``coordinates``: place pins and addresses, transport endpoints, photo GPS.
- ``gpx``: day activity tracks.
- ``note_text``: note bodies and links, lodging and transport descriptions.
- ``checklist_text``: checklist item text.

A note or checklist item marked ``is_private`` stays hidden even when its group
is on. Categories, tags, visits, and members are not part of the story.
"""
from __future__ import annotations

COLLECTION_FIELDS = (
    'id', 'name', 'description', 'type', 'start_date', 'end_date', 'timezone', 'day_count',
    'status', 'days_until_start', 'link', 'visibility', 'is_public', 'comment_access', 'created_at',
    'updated_at',
    'is_archived',
)
IMAGE_FIELDS = ('id', 'image', 'is_primary', 'source', 'content_type', 'object_id')
ITEM_FIELDS = (
    'id', 'collection', 'content_type', 'object_id', 'item', 'date', 'is_global', 'order', 'day',
    'day_index', 'span_end_index', 'is_optional', 'start_time', 'end_time', 'timezone',
    'start_datetime', 'end_datetime', 'object_name',
)
DAY_FIELDS = ('id', 'collection', 'index', 'date', 'name', 'description')


def _pick(data, fields):
    return {key: data[key] for key in fields if key in data}


def _images(images, groups):
    result = []
    for image in images or []:
        if not image:
            continue
        picked = _pick(image, IMAGE_FIELDS)
        if groups.get('coordinates'):
            picked.update(_pick(image, ('latitude', 'longitude')))
        result.append(picked)
    return result


def _attachments(attachments, groups):
    if not groups.get('attachments'):
        return []
    return [_pick(a, ('id', 'file', 'extension', 'name')) for a in attachments or [] if a]


def _location(data, groups, location_public):
    picked = _pick(data, ('id', 'name', 'is_visited'))
    picked['images'] = _images(data.get('images'), groups)
    if location_public or groups.get('place_details'):
        # A place its owner published keeps its own description and link. The
        # place_details group copies them into this story without publishing the place.
        picked.update(_pick(data, ('description', 'link', 'rating')))
    if groups.get('coordinates'):
        picked.update(_pick(data, ('latitude', 'longitude', 'location', 'city', 'region', 'country')))
    if groups.get('costs'):
        picked.update(_pick(data, ('price', 'price_currency')))
    picked['attachments'] = _attachments(data.get('attachments'), groups)
    return picked


def _lodging(data, groups):
    picked = _pick(data, ('id', 'name', 'type', 'check_in', 'check_out', 'timezone', 'collection'))
    picked['images'] = _images(data.get('images'), groups)
    if groups.get('lodging_address'):
        picked.update(_pick(data, ('location', 'latitude', 'longitude')))
    if groups.get('reservations'):
        picked.update(_pick(data, ('reservation_number', 'link')))
    if groups.get('costs'):
        picked.update(_pick(data, ('price', 'price_currency')))
    if groups.get('note_text'):
        picked.update(_pick(data, ('description',)))
    picked['attachments'] = _attachments(data.get('attachments'), groups)
    return picked


def _transportation(data, groups):
    picked = _pick(data, (
        'id', 'name', 'type', 'date', 'end_date', 'start_timezone', 'end_timezone',
        'from_location', 'to_location', 'start_code', 'end_code', 'collection',
        'distance', 'travel_duration_minutes',
    ))
    picked['images'] = _images(data.get('images'), groups)
    if groups.get('coordinates'):
        picked.update(_pick(data, (
            'origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude',
        )))
    if groups.get('reservations'):
        picked.update(_pick(data, ('flight_number', 'link')))
    if groups.get('costs'):
        picked.update(_pick(data, ('price', 'price_currency')))
    if groups.get('note_text'):
        picked.update(_pick(data, ('description',)))
    picked['attachments'] = _attachments(data.get('attachments'), groups)
    return picked


def _note(data, groups):
    picked = _pick(data, ('id', 'name', 'date', 'collection'))
    if groups.get('note_text'):
        picked.update(_pick(data, ('content', 'links')))
    return picked


def _checklist(data, groups):
    picked = _pick(data, ('id', 'name', 'date', 'collection'))
    items = []
    if groups.get('checklist_text'):
        items = [
            _pick(item, ('id', 'name', 'is_checked'))
            for item in data.get('items') or []
            if not item.get('is_private')
        ]
    picked['items'] = items
    return picked


def _activity(data, groups):
    picked = _pick(data, (
        'id', 'day', 'collection', 'trail', 'name', 'sport_type', 'distance', 'moving_time',
        'elapsed_time', 'elevation_gain', 'elevation_loss', 'day_index',
    ))
    if groups.get('gpx'):
        picked.update(_pick(data, ('gpx_file', 'geojson')))
    if groups.get('coordinates'):
        picked.update(_pick(data, ('start_lat', 'start_lng', 'end_lat', 'end_lng')))
    return picked


def _trail(data, groups):
    return _pick(data, ('id', 'name', 'day', 'collection', 'span_end_index', 'day_index', 'link', 'provider', 'wanderer_link'))


def build_story_payload(data, collection):
    """The story a public reader receives, from the member payload of ``collection``."""
    groups = {name: collection.story_group(name) for name in collection.STORY_GROUPS}

    story = _pick(data, COLLECTION_FIELDS)
    story['story_groups'] = groups
    story['primary_image'] = (_images([data.get('primary_image')], groups) or [None])[0]

    owner = next((c for c in data.get('collaborators') or [] if c.get('is_owner')), None)
    story['collaborators'] = [
        _pick(owner, ('uuid', 'username', 'first_name', 'last_name', 'profile_pic', 'public_profile', 'is_owner'))
    ] if owner and owner.get('public_profile') else []

    public_location_ids = set(
        str(pk) for pk in collection.locations.filter(is_public=True).values_list('id', flat=True)
    )
    story['locations'] = [
        _location(loc, groups, str(loc.get('id')) in public_location_ids) for loc in data.get('locations') or []
    ]
    story['lodging'] = [_lodging(item, groups) for item in data.get('lodging') or []]
    story['transportations'] = [_transportation(item, groups) for item in data.get('transportations') or []]

    private_notes = set(
        str(pk) for pk in collection.note_set.filter(is_private=True).values_list('id', flat=True)
    )
    story['notes'] = [_note(n, groups) for n in data.get('notes') or [] if str(n.get('id')) not in private_notes]
    story['checklists'] = [_checklist(c, groups) for c in data.get('checklists') or []]

    story['itinerary'] = [
        _pick(item, ITEM_FIELDS)
        for item in data.get('itinerary') or []
        if str(item.get('object_id')) not in private_notes
    ]
    story['itinerary_days'] = [_pick(day, DAY_FIELDS) for day in data.get('itinerary_days') or []]
    story['day_activities'] = [_activity(a, groups) for a in data.get('day_activities') or []]
    story['day_trails'] = [_trail(t, groups) for t in data.get('day_trails') or []]
    story['day_images'] = _images(data.get('day_images'), groups)
    return story
