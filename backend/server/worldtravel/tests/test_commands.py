from io import StringIO
from unittest.mock import patch

from django.core.management import get_commands, load_command_class
from django.test import SimpleTestCase

RENAMED = {
    'download-countries': ('worldtravel', 'download_countries'),
    'bulk-adventure-geocode': ('adventures', 'bulk_location_geocode'),
    'travel-seed': ('adventures', 'travel_seed'),
}


class RenamedCommandTests(SimpleTestCase):
    def test_new_names_and_old_aliases_are_both_registered(self):
        registered = get_commands()
        for old, (app, new) in RENAMED.items():
            with self.subTest(old=old):
                self.assertEqual(registered[new], app)
                self.assertEqual(registered[old], app)

    def test_an_alias_runs_the_new_command_and_warns(self):
        for old, (app, new) in RENAMED.items():
            with self.subTest(old=old):
                alias_app = get_commands()[old]
                alias = load_command_class(alias_app, old)
                real = load_command_class(get_commands()[new], new)
                self.assertIsInstance(alias, type(real))
                alias.stderr = StringIO()
                with patch.object(type(real), 'handle', return_value='ran') as handle:
                    self.assertEqual(alias.handle(), 'ran')
                handle.assert_called_once()
                self.assertIn(f"'{old}' is now '{new}'", alias.stderr.getvalue())
