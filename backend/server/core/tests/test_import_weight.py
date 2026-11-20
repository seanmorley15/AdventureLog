"""Guard the per-process memory footprint.

Every gunicorn worker and the job worker is its own Python process, so a heavy library imported
at URL-load time is paid for several times over. These run in a fresh interpreter because other
tests legitimately import the libraries, which would hide a regression in this process.
"""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

SERVER_DIR = Path(__file__).resolve().parents[2]

# Libraries that are only needed by specific features and must be imported on first use.
DEFERRED = ('stripe',)

PROBE = """
import sys
import django
django.setup()
import django.urls
django.urls.get_resolver().url_patterns
print('LOADED:' + ','.join(name for name in {names!r} if name in sys.modules))
"""


class ImportWeightTests(SimpleTestCase):
    def test_deferred_libraries_not_loaded_at_startup(self):
        env = {**os.environ, 'PYTHONPATH': str(SERVER_DIR), 'DJANGO_SETTINGS_MODULE': 'main.settings'}
        result = subprocess.run(
            [sys.executable, '-c', PROBE.format(names=DEFERRED)],
            cwd=SERVER_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        marker = [line for line in result.stdout.splitlines() if line.startswith('LOADED:')]
        self.assertTrue(marker, result.stdout[-2000:])
        loaded = [name for name in marker[-1][len('LOADED:'):].split(',') if name]
        self.assertEqual(
            loaded,
            [],
            f'{loaded} imported at startup; import inside the function that needs it '
            '(see core.lazy.lazy_module).',
        )
