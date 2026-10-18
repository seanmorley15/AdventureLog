"""Collection type (folder or trip) and backup schema versions.

Schema 2 added ``type``. Schema 3 added the day plan: timezone, day indexes,
placements, spans, optional flags, and local times. Schema 4 added day-owned
trails, activities, and photos. Schema 5 added visibility, member roles, guest
links, story groups, and private notes and checklist items. Import of an older
schema runs each later step in order. Import without the schema 4 or 5 keys still
succeeds: a collection without ``visibility`` is public only if it was
``is_public``, and its story groups are off.
"""

from datetime import date

TYPE_SCHEMA = 2
DAY_PLAN_SCHEMA = 3
DAY_FILES_SCHEMA = 4
VISIBILITY_SCHEMA = 5
BACKUP_SCHEMA = VISIBILITY_SCHEMA

FOLDER = 'folder'
TRIP = 'trip'
COLLECTION_TYPES = (FOLDER, TRIP)


class UnsupportedBackupSchema(Exception):
    def __init__(self, schema):
        self.schema = schema
        super().__init__('This backup uses a newer schema than this server supports.')


def assign_collection_type_from_dates(start_date, end_date):
    """Set type from dates.

    Both dates mean trip, of any length.
    One date or neither means folder. The dates themselves are unchanged.
    """
    if start_date and end_date:
        return TRIP
    return FOLDER


def parse_backup_schema(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError('Invalid backup schema.')
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped.lstrip('-').isdigit():
            raise ValueError('Invalid backup schema.')
        return int(stripped)
    return int(value)


def ensure_backup_schema_supported(value):
    schema = parse_backup_schema(value)
    if schema is not None and schema > BACKUP_SCHEMA:
        raise UnsupportedBackupSchema(schema)
    return schema


def resolve_imported_collection_type(backup_schema, start_date, end_date, type_value):
    """Run import migrations through the current schema.

    A file with no schema, or schema 1, sets type from its dates. Schema 2
    and later keep an explicit folder or trip. A newer schema is rejected
    and is not imported with unknown keys dropped.
    """
    schema = ensure_backup_schema_supported(backup_schema)
    if schema is None or schema < TYPE_SCHEMA:
        return assign_collection_type_from_dates(start_date, end_date)
    if type_value in COLLECTION_TYPES:
        return type_value
    return assign_collection_type_from_dates(start_date, end_date)


def backup_has_day_plan(backup_schema):
    """True when the file stores days and placements (schema 3 or later)."""
    schema = parse_backup_schema(backup_schema)
    return schema is not None and schema >= DAY_PLAN_SCHEMA


def imported_visibility(backup_schema, col_data):
    """Schema 5 stores visibility. An older file is public only if it was is_public."""
    schema = parse_backup_schema(backup_schema)
    if schema is not None and schema >= VISIBILITY_SCHEMA and col_data.get('visibility') in (
        'private', 'unlisted', 'public'
    ):
        return col_data['visibility']
    return 'public' if col_data.get('is_public') else 'private'


def imported_story_groups(backup_schema, col_data, known_groups):
    """Story groups are off unless a schema 5 file turned them on."""
    schema = parse_backup_schema(backup_schema)
    if schema is None or schema < VISIBILITY_SCHEMA:
        return {}
    groups = col_data.get('story_groups') or {}
    if not isinstance(groups, dict):
        return {}
    return {name: True for name in known_groups if groups.get(name) is True}


def collection_lifecycle_status(collection, today=None):
    """upcoming, in_progress, or completed. Null when either date is missing."""
    if not collection.start_date or not collection.end_date:
        return None
    today = today or date.today()
    if collection.start_date > today:
        return 'upcoming'
    if collection.end_date < today:
        return 'completed'
    return 'in_progress'
