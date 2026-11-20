"""The shape of the code base, kept from drifting back."""

import ast

from django.test import SimpleTestCase

from core.tests.test_references import FIRST_PARTY, ROOT, SKIP_DIRS

# The largest modules are around 800 lines. Past this, split by what the module is about.
MAX_MODULE_LINES = 900


def modules():
    for path in sorted(ROOT.rglob('*.py')):
        parts = path.relative_to(ROOT).parts
        if SKIP_DIRS.intersection(parts) or parts[0] not in FIRST_PARTY or 'migrations' in parts:
            continue
        yield path


class CodeLayoutTests(SimpleTestCase):
    def test_every_package_says_what_it_is_for(self):
        missing = [
            str(path.relative_to(ROOT))
            for path in modules()
            if path.name == '__init__.py'
            and 'tests' not in path.parts
            and 'management' not in path.parts
            and not ast.get_docstring(ast.parse(path.read_text()))
        ]
        self.assertEqual(missing, [], 'Add a one-line docstring to: ' + ', '.join(missing))

    def test_no_module_has_grown_into_a_dumping_ground(self):
        too_long = {
            str(path.relative_to(ROOT)): len(path.read_text().splitlines())
            for path in modules()
            if len(path.read_text().splitlines()) > MAX_MODULE_LINES
        }
        self.assertEqual(too_long, {}, f'Split these by what they are about (limit {MAX_MODULE_LINES} lines)')

    def test_view_modules_are_named_after_their_resource(self):
        stale = [
            str(path.relative_to(ROOT))
            for path in modules()
            if path.parent.name == 'views' and path.stem.endswith('_view')
        ]
        self.assertEqual(stale, [], 'Name view modules after the resource, without a _view suffix')

    def test_management_commands_use_snake_case_names(self):
        deprecated_aliases = {'download-countries', 'bulk-adventure-geocode', 'travel-seed'}
        hyphenated = [
            path.stem
            for path in modules()
            if path.parent.name == 'commands' and '-' in path.stem and path.stem not in deprecated_aliases
        ]
        self.assertEqual(hyphenated, [])
