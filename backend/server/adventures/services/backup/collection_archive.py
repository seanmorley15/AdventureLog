"""One collection as a file: download it, or add it to an account."""

import json
import re
import zipfile

from django.db import transaction

from adventures.services.media_quota import enforce_media_storage_limit, zip_media_bytes

from .errors import BackupError
from .exporter import COLLECTION_ARCHIVE, BackupExporter
from .legacy import LEGACY_DATA_FILE, upgrade_legacy_metadata
from .restorer import (
    EXISTING_LOCATION_CHOICES,
    LINK_EXISTING_LOCATIONS,
    BackupRestorer,
    RestoreOptions,
)
from .service import DATA_FILE, ArchiveFile, build_archive, ensure_schema_supported, read_data_file


def export_collection_archive(user, collection):
    # The name ends up in a Content-Disposition header, so keep it to one safe line.
    name = re.sub(r'["\r\n\\]', '', collection.name).replace(' ', '_')
    return ArchiveFile(content=build_archive(BackupExporter(user, collection)), filename=f'collection-{name}.zip')


def _read_collection_data(archive):
    names = archive.namelist()
    if DATA_FILE in names:
        data = read_data_file(archive)
        if data.get('archive_kind') != COLLECTION_ARCHIVE:
            raise BackupError(
                'This file is a full backup, not a single collection. '
                'Restore it from Settings instead.'
            )
        ensure_schema_supported(data)
        return data

    if LEGACY_DATA_FILE in names:
        try:
            metadata = json.loads(archive.read(LEGACY_DATA_FILE).decode('utf-8'))
        except json.JSONDecodeError:
            raise BackupError('Invalid JSON in collection file')
        # Older files can be newer than this server: upgrade refuses those.
        ensure_schema_supported(metadata)
        return upgrade_legacy_metadata(metadata, archive)

    raise BackupError('Invalid collection file - missing data.json')


def restore_collection_archive(upload, user, existing_locations=LINK_EXISTING_LOCATIONS):
    """
    Add the collection in a file to the user's account, next to what they already have.

    ``existing_locations`` decides what happens to a place in the file that the user already
    has: ``link`` puts the place they have into the new collection, ``create`` makes a new one.
    Returns the restore result; its first collection is the new one.
    """
    if existing_locations not in EXISTING_LOCATION_CHOICES:
        raise BackupError(
            "existing_locations must be 'link' or 'create'."
        )

    with zipfile.ZipFile(upload, 'r') as archive:
        data = _read_collection_data(archive)
        if len(data.get('collections') or []) != 1:
            raise BackupError('A collection file must contain exactly one collection.')

        allowed, details = enforce_media_storage_limit(user, zip_media_bytes(archive))
        if not allowed:
            raise BackupError('Media storage limit exceeded', status=413, extra=details)

        options = RestoreOptions(unique_collection_names=True, existing_locations=existing_locations)
        with transaction.atomic():
            result = BackupRestorer(data, archive, user, options).restore()
            # The restorer builds rows from the file's text (dates as strings); hand back what was stored.
            for collection in result.collections:
                collection.refresh_from_db()
            return result
