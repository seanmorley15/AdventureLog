"""
Import an exported AdventureLog zip into a user's account from the command line.

Handles both kinds of export:
  * a full account backup (Settings > Export). Restoring REPLACES everything in the account,
    so it needs --yes.
  * a single collection archive. This is added next to what the account already has.

Usage:
    python manage.py import_backup backup.zip --user alice --yes
    python manage.py import_backup trip.zip --user alice
    python manage.py import_backup trip.zip --user alice --existing-locations create

In Docker:
    docker compose cp backup.zip server:/tmp/backup.zip
    docker compose exec server python3 manage.py import_backup /tmp/backup.zip --user alice --yes
"""

import zipfile

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from adventures.services.backup.collection_archive import restore_collection_archive
from adventures.services.backup.errors import BackupError
from adventures.services.backup.exporter import COLLECTION_ARCHIVE
from adventures.services.backup.restorer import EXISTING_LOCATION_CHOICES, LINK_EXISTING_LOCATIONS
from adventures.services.backup.service import read_data_file, restore_account_backup

User = get_user_model()


class Command(BaseCommand):
    help = 'Import an exported AdventureLog zip (account backup or collection archive) into a user account'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Path to the exported .zip file')
        parser.add_argument('--user', required=True, help='Username or email of the account to import into')
        parser.add_argument(
            '--yes', action='store_true',
            help='Confirm a full account restore, which deletes everything in the account first',
        )
        parser.add_argument(
            '--existing-locations', choices=EXISTING_LOCATION_CHOICES, default=LINK_EXISTING_LOCATIONS,
            help='Collection archives only: for places you already have, "link" uses yours, "create" makes copies (default: link)',
        )

    def handle(self, *args, **options):
        user = self._find_user(options['user'])
        path = options['file']

        try:
            with open(path, 'rb') as upload:
                if not zipfile.is_zipfile(upload):
                    raise CommandError(f'{path} is not a zip archive.')
                upload.seek(0)
                with zipfile.ZipFile(upload) as archive:
                    kind = read_data_file(archive).get('archive_kind')
                upload.seek(0)

                if kind == COLLECTION_ARCHIVE:
                    self._import_collection(upload, user, options['existing_locations'])
                else:
                    self._import_account(upload, user, options['yes'])
        except FileNotFoundError:
            raise CommandError(f'File not found: {path}')
        except BackupError as exc:
            raise CommandError(f'{exc.code}: {exc}')
        except zipfile.BadZipFile:
            raise CommandError(f'{path} is not a valid zip archive.')

    def _find_user(self, identifier):
        users = User.objects.filter(username=identifier)
        if not users.exists():
            users = User.objects.filter(email__iexact=identifier)
        if users.count() > 1:
            raise CommandError(f'More than one user matches "{identifier}"; use the username.')
        user = users.first()
        if user is None:
            raise CommandError(f'No user found with username or email "{identifier}".')
        return user

    def _import_account(self, upload, user, confirmed):
        if not confirmed:
            raise CommandError(
                f'Restoring a full backup deletes everything in the account "{user.username}" first. '
                'Re-run with --yes to confirm.'
            )
        self.stdout.write(f'Restoring full backup into "{user.username}"...')
        try:
            summary = restore_account_backup(upload, user)
        except BackupError:
            raise
        except Exception as exc:
            # The restore runs in a transaction, so nothing was changed.
            raise CommandError(f'The file could not be imported ({exc}). The account was not changed.')
        self._print_summary(summary)

    def _import_collection(self, upload, user, existing_locations):
        self.stdout.write(f'Importing collection archive into "{user.username}"...')
        try:
            result = restore_collection_archive(upload, user, existing_locations)
        except BackupError:
            raise
        except Exception as exc:
            raise CommandError(f'The file could not be imported ({exc}). The account was not changed.')
        for collection in result.collections:
            self.stdout.write(f'Collection: {collection.name} ({collection.id})')
        self._print_summary(result.summary)

    def _print_summary(self, summary):
        self.stdout.write(self.style.SUCCESS('Import complete:'))
        for key, count in summary.items():
            if count:
                self.stdout.write(f'  {key.replace("_", " ")}: {count}')
