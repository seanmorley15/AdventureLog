import os
import tempfile
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from adventures.models import Collection, Location
from adventures.services.backup.collection_archive import export_collection_archive
from adventures.services.backup.service import export_account_backup
from core.geo import make_point
from users.models import CustomUser


class ImportBackupCommandTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(username='cmd-owner', email='owner@example.com', password='x')
        self.target = CustomUser.objects.create_user(username='cmd-target', email='target@example.com', password='x')
        self.trip = Collection.objects.create(user=self.owner, name='Japan', start_date=date(2019, 3, 20))
        place = Location(user=self.owner, name='Fushimi Inari', coordinates=make_point(135.77, 34.96))
        place.save(_skip_geocode=True)
        self.trip.locations.add(place)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, content):
        path = os.path.join(self.tmp.name, name)
        with open(path, 'wb') as handle:
            handle.write(content)
        return path

    def run_command(self, *args):
        out = StringIO()
        call_command('import_backup', *args, stdout=out)
        return out.getvalue()

    def test_a_full_backup_needs_confirmation(self):
        path = self.write('backup.zip', export_account_backup(self.owner).content)

        with self.assertRaises(CommandError):
            self.run_command(path, '--user', 'cmd-target')

        self.assertEqual(Location.objects.filter(user=self.target).count(), 0)

    def test_a_full_backup_is_restored(self):
        path = self.write('backup.zip', export_account_backup(self.owner).content)

        output = self.run_command(path, '--user', 'target@example.com', '--yes')

        self.assertEqual(Location.objects.filter(user=self.target, name='Fushimi Inari').count(), 1)
        self.assertIn('Import complete', output)

    def test_a_collection_archive_is_added_without_confirmation(self):
        path = self.write('trip.zip', export_collection_archive(self.owner, self.trip).content)

        self.run_command(path, '--user', 'cmd-target')

        self.assertTrue(Collection.objects.filter(user=self.target, name='Japan').exists())

    def test_bad_input_is_reported(self):
        not_a_zip = self.write('bad.zip', b'nope')
        for args in ([not_a_zip, '--user', 'cmd-target'], ['/missing.zip', '--user', 'cmd-target'], [not_a_zip, '--user', 'ghost']):
            with self.assertRaises(CommandError):
                self.run_command(*args)
