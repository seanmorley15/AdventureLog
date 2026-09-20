"""
Django settings for automated tests (CI and local).

Imports production settings, then overrides cache, password hashing, media paths,
and auth-related flags so a developer `.env` cannot change suite defaults.
"""

import tempfile
from pathlib import Path

from main.settings import *  # noqa: F401, F403

# In-memory cache — avoids requiring memcached in CI/local test runs.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'adventurelog-tests',
    }
}

# Faster password hashing for test user creation.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

_test_dir = Path(tempfile.mkdtemp(prefix='adventurelog-test-'))
MEDIA_ROOT = _test_dir / 'media'
STATIC_ROOT = _test_dir / 'staticfiles'
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
STATIC_ROOT.mkdir(parents=True, exist_ok=True)

# Hermetic auth defaults (ignore local .env pollution).
DISABLE_REGISTRATION = False
DISABLE_REGISTRATION_MESSAGE = (
    'Registration is disabled. Please contact the administrator if you need an account.'
)
TERMS_OF_SERVICE_URL = ''
PRIVACY_POLICY_URL = ''
ACCOUNT_PASSWORD_MIN_LENGTH = 10
AUTH_PASSWORD_VALIDATORS_ENABLED = False
AUTH_PASSWORD_VALIDATORS = []
ACCOUNT_EMAIL_VERIFICATION = 'none'
FRONTEND_URL = 'http://localhost:3000'
LOGIN_REDIRECT_URL = FRONTEND_URL
INVITATIONS_SIGNUP_REDIRECT_URL = f'{FRONTEND_URL}/signup'
INVITATIONS_SIGNUP_REDIRECT = f'{FRONTEND_URL}/signup'
HEADLESS_FRONTEND_URLS = {
    'account_confirm_email': f'{FRONTEND_URL}/user/verify-email/{{key}}',
    'account_reset_password': f'{FRONTEND_URL}/user/reset-password',
    'account_reset_password_from_key': f'{FRONTEND_URL}/user/reset-password/{{key}}',
    'account_signup': f'{FRONTEND_URL}/signup',
    'socialaccount_login_error': f'{FRONTEND_URL}/account/provider/callback',
}
