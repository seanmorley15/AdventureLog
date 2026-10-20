"""Whole-account backups: the operations the backup endpoints call."""

import json
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction

from adventures.utils.collection_type import UnsupportedBackupSchema, ensure_backup_schema_supported
from adventures.services.media_quota import enforce_media_storage_limit, user_content_media_names, zip_media_bytes
from adventures.services.account_data import clear_user_adventure_data

from .errors import BackupError
from .exporter import COLLECTION_ARCHIVE, BackupExporter
from .restorer import BackupRestorer

DATA_FILE = 'data.json'


@dataclass
class ArchiveFile:
    content: bytes
    filename: str


def build_archive(exporter):
    """The zip of an exporter's JSON and files, as bytes."""
    data = exporter.build()
    with tempfile.TemporaryFile(suffix='.zip') as spool:
        with zipfile.ZipFile(spool, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(DATA_FILE, json.dumps(data, indent=2))
            exporter.write_media(archive)
        spool.seek(0)
        return spool.read()


def read_data_file(archive):
    """The parsed JSON of an archive, or a BackupError saying why it cannot be used."""
    if DATA_FILE not in archive.namelist():
        raise BackupError('Invalid backup file - missing data.json')
    try:
        return json.loads(archive.read(DATA_FILE).decode('utf-8'))
    except json.JSONDecodeError:
        raise BackupError('Invalid JSON in backup file')


def ensure_schema_supported(data):
    try:
        ensure_backup_schema_supported(data.get('backup_schema'))
    except UnsupportedBackupSchema:
        raise BackupError('This backup uses a newer schema than this server supports.')
    except ValueError:
        raise BackupError('Invalid backup schema.')


def export_account_backup(user):
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return ArchiveFile(
        content=build_archive(BackupExporter(user)),
        filename=f'adventurelog_backup_{user.username}_{stamp}.zip',
    )


def restore_account_backup(upload, user):
    """Replace everything the user has with the contents of a backup file. Returns the summary."""
    with zipfile.ZipFile(upload, 'r') as archive:
        data = read_data_file(archive)
        if data.get('archive_kind') == COLLECTION_ARCHIVE:
            # Restoring this would erase the account first and bring back a single collection.
            raise BackupError(
                'This file is a single collection, not a full backup. '
                'Import it from the Collections page instead.'
            )
        ensure_schema_supported(data)

        # The import replaces the user's photos and files, so only the new ones count.
        allowed, details = enforce_media_storage_limit(
            user, zip_media_bytes(archive), exclude_names=user_content_media_names(user)
        )
        if not allowed:
            raise BackupError('Media storage limit exceeded', status=413, extra=details)

        with transaction.atomic():
            clear_user_adventure_data(user)
            return BackupRestorer(data, archive, user).restore().summary
