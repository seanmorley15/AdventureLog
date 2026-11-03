"""Replace the values of a backup that change from run to run, keeping its structure."""

import copy
import json
import os
import re
import zipfile
from pathlib import Path

UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
GOLDEN_DIR = Path(__file__).parent / 'golden'
VOLATILE_KEYS = {'export_date', 'created_at'}
TOKEN_KEYS = {'token', 'author_guest_token'}
FILENAME_KEYS = {'filename', 'gpx_filename'}


class Normalizer:
    """Numbers each distinct uuid, token and file name in the order it is first seen."""

    def __init__(self, users=None):
        self.seen = {}
        self.users = {str(uuid): name for uuid, name in (users or {}).items()}

    def _label(self, kind, value):
        return self.seen.setdefault((kind, value), f'<{kind}-{sum(1 for k in self.seen if k[0] == kind) + 1}>')

    def data(self, value, key=None):
        if isinstance(value, dict):
            return {k: self.data(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [self.data(v, key) for v in value]
        if value is None:
            return None
        if key in VOLATILE_KEYS:
            return f'<{key}>'
        if key in TOKEN_KEYS:
            return self._label('token', value)
        if key in FILENAME_KEYS:
            return self._label('file', value)
        if key == 'country' and isinstance(value, int) and not isinstance(value, bool):
            return '<country-pk>'
        if isinstance(value, str) and value in self.users:
            return f'<user-{self.users[value]}>'
        if isinstance(value, str) and UUID.match(value):
            return self._label('uuid', value)
        return value

    def member(self, name):
        folder, _, filename = name.partition('/')
        return f'{folder}/{self._label("file", filename)}' if filename else name


def read_archive(content, data_name='data.json', users=None):
    """(normalized data.json, sorted normalized zip member names) of a downloaded archive."""
    import io

    normalizer = Normalizer(users)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        data = json.loads(archive.read(data_name).decode('utf-8'))
        normalized = normalizer.data(copy.deepcopy(data))
        members = sorted(normalizer.member(n) for n in archive.namelist() if n != data_name)
    return normalized, members


def assert_matches_golden(testcase, name, actual):
    path = GOLDEN_DIR / name
    if os.environ.get('REGEN_GOLDEN'):
        path.write_text(json.dumps(actual, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    expected = json.loads(path.read_text(encoding='utf-8'))
    testcase.assertEqual(json.loads(json.dumps(actual, sort_keys=True)), expected)
