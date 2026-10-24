"""Settings for `manage.py test`.

Database credentials still come from the environment via `main.settings`.
Policy flags, cache, and background work are pinned so a developer `.env`
cannot change assertions or start geocode threads during the suite.
"""

from .settings import *  # noqa: F403

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

TERMS_OF_SERVICE_URL = ''
PRIVACY_POLICY_URL = ''
DISABLE_REGISTRATION = False
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_PASSWORD_MIN_LENGTH = 10
AUTH_PASSWORD_VALIDATORS_ENABLED = False
AUTH_PASSWORD_VALIDATORS = []

# Location.save starts a geocode thread that outlives the test transaction.
DISABLE_BACKGROUND_GEOCODE = True
