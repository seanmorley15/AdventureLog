"""Collection type (folder or trip) and backup schema versions.

Schema 2 added ``type``. Schema 3 added the day plan: timezone, day indexes,
placements, spans, optional flags, and local times. Import of an older schema
runs each later step in order; see ``backup_needs_day_conversion``.
"""

from datetime import date

TYPE_SCHEMA = 2
DAY_PLAN_SCHEMA = 3
BACKUP_SCHEMA = DAY_PLAN_SCHEMA

FOLDER = 'folder'
TRIP = 'trip'
COLLECTION_TYPES = (FOLDER, TRIP)


class UnsupportedBackupSchema(Exception):
    def __init__(self, schema):
        self.schema = schema
        super().__init__('This backup uses a newer schema than this server supports.')


def assign_collection_type_from_dates(start_date, end_date):
    """Set type from dates.

    Both dates mean trip, including a range longer than 21 days.
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
