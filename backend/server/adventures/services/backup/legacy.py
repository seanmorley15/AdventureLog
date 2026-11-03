"""Reading the old single-collection file (``metadata.json``) with the current restorer.

That format only described a collection's places, transport, notes, checklists and lodging.
Rather than keep a second importer, the old file is rewritten as the current format and
restored the same way. The old file stored no day plan, so it is marked as a schema 2 file
and the restorer rebuilds the plan from the records' dates.
"""

from datetime import datetime

from adventures.utils.collection_type import TYPE_SCHEMA
from core.parsing import parse_iso_date

from .exporter import COLLECTION_ARCHIVE

LEGACY_DATA_FILE = 'metadata.json'


def _date(value):
    parsed = parse_iso_date(value)
    return parsed.isoformat() if parsed else None


def _datetime(value):
    """An ISO timestamp (a trailing Z allowed) as normalized ISO text, or None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _member(archive, prefix):
    return next((name for name in archive.namelist() if name.startswith(prefix)), None)


def upgrade_legacy_metadata(metadata, archive):
    """The metadata.json of an old collection export, as the current backup format."""
    collection_meta = metadata.get('collection') or {}
    image_meta = {img['export_id']: img for img in metadata.get('images', [])}
    attachment_meta = {att['export_id']: att for att in metadata.get('attachments', [])}

    categories, locations, cover = [], [], None
    for index, loc_data in enumerate(metadata.get('locations', [])):
        category = loc_data.get('category')
        if category and category not in [c['name'] for c in categories]:
            categories.append({'name': category, 'display_name': category, 'icon': '🌍'})

        images = []
        for export_id in loc_data.get('images', []):
            meta = image_meta.get(export_id)
            member = _member(archive, f'images/{export_id}-') if meta else None
            if not member:
                continue
            if meta.get('is_primary'):
                cover = {'content_type': 'location', 'location_export_id': index, 'image_index': len(images)}
            images.append({'filename': member[len('images/'):], 'is_primary': bool(meta.get('is_primary'))})

        attachments = []
        for export_id in loc_data.get('attachments', []):
            meta = attachment_meta.get(export_id)
            if meta:
                name = meta.get('name', '')
                attachments.append({'name': name, 'filename': name})

        # The old file named a place's city, region and country but never restored them, so
        # they are left out rather than passed to code that expects ids.
        locations.append({
            'export_id': index,
            'name': loc_data.get('name') or 'Untitled',
            'description': loc_data.get('description'),
            'location': loc_data.get('location'),
            'tags': loc_data.get('tags') or [],
            'rating': loc_data.get('rating'),
            'link': loc_data.get('link'),
            'is_public': bool(loc_data.get('is_public', False)),
            'latitude': loc_data.get('latitude'),
            'longitude': loc_data.get('longitude'),
            'category_name': category,
            'collection_export_ids': [0],
            'images': images,
            'attachments': attachments,
        })

    collection = {
        'export_id': 0,
        'name': collection_meta.get('name') or 'Imported Collection',
        'description': collection_meta.get('description'),
        'is_public': collection_meta.get('is_public', False),
        'is_archived': collection_meta.get('is_archived', False),
        'start_date': _date(collection_meta.get('start_date')),
        'end_date': _date(collection_meta.get('end_date')),
        'type': collection_meta.get('type'),
        'timezone': collection_meta.get('timezone'),
        'link': collection_meta.get('link'),
        'day_count': collection_meta.get('day_count'),
    }
    if cover:
        collection['primary_image'] = cover

    return {
        'backup_schema': TYPE_SCHEMA,
        'archive_kind': COLLECTION_ARCHIVE,
        'categories': categories,
        'collections': [collection],
        'locations': locations,
        'transportation': [
            {
                'type': t.get('type') or t.get('transportation_type') or 'other',
                'name': t.get('name') or 'Untitled Transportation',
                'description': t.get('description') or t.get('notes'),
                'rating': t.get('rating'),
                'price': t.get('price'),
                'price_currency': t.get('price_currency'),
                'link': t.get('link'),
                'date': _datetime(t.get('date')),
                'end_date': _datetime(t.get('end_date')),
                'start_timezone': t.get('start_timezone'),
                'end_timezone': t.get('end_timezone'),
                'flight_number': t.get('flight_number'),
                'from_location': t.get('from_location'),
                'to_location': t.get('to_location'),
                'origin_latitude': t.get('origin_latitude'),
                'origin_longitude': t.get('origin_longitude'),
                'destination_latitude': t.get('destination_latitude'),
                'destination_longitude': t.get('destination_longitude'),
                'start_code': t.get('start_code'),
                'end_code': t.get('end_code'),
                'is_public': bool(t.get('is_public', False)),
                'collection_export_id': 0,
            }
            for t in metadata.get('transportation', [])
        ],
        'notes': [
            {
                'name': n.get('name') or n.get('title') or 'Untitled Note',
                'content': n.get('content') or '',
                'links': n.get('links') or [],
                'date': _date(n.get('date')),
                'is_public': bool(n.get('is_public', False)),
                'collection_export_id': 0,
            }
            for n in metadata.get('notes', [])
        ],
        'checklists': [
            {
                'name': c.get('name') or 'Untitled Checklist',
                'date': _date(c.get('date')),
                'is_public': bool(c.get('is_public', False)),
                'collection_export_id': 0,
                'items': [
                    {
                        'name': item.get('name') or 'Untitled Item',
                        'is_checked': item.get('is_checked', item.get('completed', False)),
                    }
                    for item in c.get('items', [])
                ],
            }
            for c in metadata.get('checklists', [])
        ],
        'lodging': [
            {
                'name': l.get('name') or 'Untitled Lodging',
                'type': l.get('type') or l.get('lodging_type') or 'other',
                'description': l.get('description') or l.get('notes'),
                'rating': l.get('rating'),
                'link': l.get('link'),
                'check_in': _datetime(l.get('check_in')),
                'check_out': _datetime(l.get('check_out')),
                'timezone': l.get('timezone'),
                'reservation_number': l.get('reservation_number'),
                'price': l.get('price'),
                'price_currency': l.get('price_currency'),
                'latitude': l.get('latitude'),
                'longitude': l.get('longitude'),
                'location': l.get('location'),
                'is_public': bool(l.get('is_public', False)),
                'collection_export_id': 0,
            }
            for l in metadata.get('lodging', [])
        ],
    }
