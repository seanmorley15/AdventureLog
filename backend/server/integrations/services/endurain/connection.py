"""Endurain server URLs and the headers every request carries."""

from core.net import self_hosted_session
from integrations.errors import IntegrationError
from integrations.services import server_urls


ENDURAIN_API_PREFIX = '/api/v1'


ENDURAIN_CLIENT_TYPE = 'mobile'


# CFNetwork suffix lets Endurain's ua-parser treat this as the client name
# (shows as "Other - AdventureLog Integration" in sessions instead of "Python Requests").
ENDURAIN_USER_AGENT = 'AdventureLog Integration/1.0 CFNetwork/1.0'


REQUEST_TIMEOUT_SECONDS = 15


def _error(message):
    return IntegrationError(message, code='endurain.invalid_server_url')


def format_server_url(server_url: str) -> str:
    """Strip and structurally validate a server URL without DNS lookups."""
    return server_urls.format_server_url(server_url, _error)


def assert_host_not_metadata(hostname: str) -> None:
    """Reject cloud-metadata / link-local targets (SSRF hardening)."""
    server_urls.assert_host_allowed(hostname, 'Endurain', _error)


def normalize_server_url(server_url: str) -> str:
    """
    Normalize and validate an Endurain base URL.

    Private/loopback hosts are allowed so self-hosted LAN Endurain works.
    Link-local / cloud-metadata targets and credentialed URLs are rejected.
    """
    return server_urls.normalize_server_url(server_url, 'Endurain', _error)


def api_url(server_url: str, path: str) -> str:
    # Stored URLs were validated at connect time; avoid DNS on every API call.
    base = format_server_url(server_url)
    if not path.startswith('/'):
        path = f'/{path}'
    return f'{base}{ENDURAIN_API_PREFIX}{path}'


def mobile_headers(access_token: str | None = None, extra: dict | None = None) -> dict:
    headers = {
        'X-Client-Type': ENDURAIN_CLIENT_TYPE,
        'User-Agent': ENDURAIN_USER_AGENT,
    }
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
    if extra:
        headers.update(extra)
    return headers


def endurain_post(url, **kwargs):
    """POST to the user's Endurain server. Never dials a metadata or link-local address."""
    with self_hosted_session() as session:
        return session.post(url, **kwargs)


def endurain_request(method, url, **kwargs):
    with self_hosted_session() as session:
        return session.request(method, url, **kwargs)
