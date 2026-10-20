"""Endurain: sign in, read activities, and export them as GPX.

``connection`` holds server URLs and headers, ``auth`` signs in and refreshes tokens,
``client`` calls the API, ``activities`` and ``gpx`` shape what comes back.
"""

from .activities import normalize_activity
from .auth import (
    consume_mfa_pending,
    create_mfa_pending,
    decode_jwt_sub,
    login_with_password,
    refresh_tokens,
    refresh_tokens_if_needed,
    verify_mfa,
)
from .client import (
    fetch_activity_by_id,
    fetch_user_activities,
    save_integration_from_tokens,
    validate_connection,
)
from .connection import ENDURAIN_USER_AGENT, normalize_server_url
from .gpx import export_activity_gpx, safe_gpx_filename

__all__ = [
    'ENDURAIN_USER_AGENT', 'consume_mfa_pending', 'create_mfa_pending', 'decode_jwt_sub',
    'export_activity_gpx', 'fetch_activity_by_id', 'fetch_user_activities', 'login_with_password',
    'normalize_activity', 'normalize_server_url', 'refresh_tokens', 'refresh_tokens_if_needed',
    'safe_gpx_filename', 'save_integration_from_tokens', 'validate_connection', 'verify_mfa',
]
