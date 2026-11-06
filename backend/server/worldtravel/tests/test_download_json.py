import shutil
import tempfile
from unittest.mock import MagicMock, patch

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import SimpleTestCase

from worldtravel.management.commands.download_countries import Command

PATH = 'test-download-countries.json'
COMMAND = 'worldtravel.management.commands.download_countries'


def fake_response(status=200, chunks=(b'{"a":', b'1}')):
    response = MagicMock()
    response.status_code = status
    response.iter_content.return_value = iter(chunks)
    response.__enter__.return_value = response
    return response


class TempStorageMixin:
    """Run against a throwaway directory. These commands list and delete files, so they must never
    see the real media folder, which holds the dataset a running server reads."""

    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.storage = FileSystemStorage(location=self.media)
        patcher = patch(f'{COMMAND}.default_storage', self.storage)
        patcher.start()
        self.addCleanup(patcher.stop)


class DownloadJsonTests(TempStorageMixin, SimpleTestCase):
    def test_streams_the_whole_file_into_storage(self):
        with patch(f'{COMMAND}.requests.get', return_value=fake_response()) as get:
            self.assertTrue(Command()._download_json(PATH))
        self.assertTrue(get.call_args.kwargs['stream'])
        with self.storage.open(PATH) as saved:
            self.assertEqual(saved.read(), b'{"a":1}')

    def test_a_failed_status_stores_nothing(self):
        with patch(f'{COMMAND}.requests.get', return_value=fake_response(404)):
            self.assertFalse(Command()._download_json(PATH))
        self.assertFalse(self.storage.exists(PATH))

    def test_a_dropped_connection_stores_nothing(self):
        response = fake_response()
        response.iter_content.side_effect = requests.ConnectionError('reset')
        with patch(f'{COMMAND}.requests.get', return_value=response):
            self.assertFalse(Command()._download_json(PATH))
        self.assertFalse(self.storage.exists(PATH))


class RemoveOldJsonTests(TempStorageMixin, SimpleTestCase):
    OLD = ['countries+regions+states-v2.5.json', 'countries_states_cities.json']
    CURRENT = 'countries+regions+states-v9.9.json'

    def test_removes_earlier_versions_and_keeps_the_current_one(self):
        for name in [*self.OLD, self.CURRENT, 'unrelated.txt']:
            self.storage.save(name, ContentFile(b'x'))
        Command()._remove_old_json(self.CURRENT)
        for name in self.OLD:
            self.assertFalse(self.storage.exists(name), name)
        self.assertTrue(self.storage.exists(self.CURRENT))
        self.assertTrue(self.storage.exists('unrelated.txt'))

    def test_a_storage_that_cannot_list_keeps_everything(self):
        self.storage.save(self.OLD[0], ContentFile(b'x'))
        with patch.object(self.storage, 'listdir', side_effect=NotImplementedError):
            Command()._remove_old_json(self.CURRENT)
        self.assertTrue(self.storage.exists(self.OLD[0]))
