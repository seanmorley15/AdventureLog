"""Google place photos, served through the app so the Google API key never reaches a browser.

Search and recommendation results carry ``/api/places/photo/?...`` paths instead of Google
addresses. The browser asks the app for the picture; the app asks Google with the key (in a
request header where Google allows it, so the key is never in a URL or a log line) and relays
the image bytes.
"""

import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from django.conf import settings

from adventures.services.images.fetch import download_remote_image

PHOTO_PROXY_PATH = '/api/places/photo/'

DEFAULT_SIZE = 800
MAX_SIZE = 1600
PHOTO_TIMEOUT = 10

# What Google hands out: `places/<id>/photos/<id>` (Places API v1) or a long opaque token (legacy).
PHOTO_NAME_RE = re.compile(r'^places/[A-Za-z0-9_-]{1,300}/photos/[A-Za-z0-9_-]{1,1000}$')
PHOTO_REFERENCE_RE = re.compile(r'^[A-Za-z0-9_-]{1,2000}$')

# Formats a browser draws as a picture. SVG is left out on purpose: it can carry script.
SAFE_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif')

_V1_MEDIA_URL = 'https://places.googleapis.com/v1/{name}/media'
_LEGACY_PHOTO_URL = 'https://maps.googleapis.com/maps/api/place/photo'


class PhotoError(Exception):
    """A photo could not be served. The message is safe to show; ``code`` and ``status`` map to the API error."""

    def __init__(self, message: str, code: str, status: int):
        super().__init__(message)
        self.code = code
        self.status = status


def proxy_photo_url(*, name: Optional[str] = None, reference: Optional[str] = None, size: int = DEFAULT_SIZE) -> str:
    """The app-relative address for a Google photo. Give a v1 photo ``name`` or a legacy ``reference``."""
    if name:
        params = {'name': name}
    elif reference:
        params = {'reference': reference}
    else:
        raise ValueError('A photo name or reference is required.')
    params['size'] = size
    return f'{PHOTO_PROXY_PATH}?{urlencode(params)}'


def parse_proxy_photo_url(value: str) -> Optional[Tuple[Optional[str], Optional[str], int]]:
    """
    Read an address made by ``proxy_photo_url``.

    Returns ``(name, reference, size)``, or ``None`` when ``value`` is not one of ours (a full
    web address, another path, or a malformed photo id).
    """
    parsed = urlparse((value or '').strip())
    if parsed.scheme or parsed.netloc or parsed.path != PHOTO_PROXY_PATH:
        return None
    query = parse_qs(parsed.query)
    name = (query.get('name') or [None])[0]
    reference = (query.get('reference') or [None])[0]
    try:
        size = int((query.get('size') or [DEFAULT_SIZE])[0])
    except ValueError:
        return None
    if bool(name) == bool(reference) or not 1 <= size <= MAX_SIZE:
        return None
    if name and not PHOTO_NAME_RE.match(name):
        return None
    if reference and not PHOTO_REFERENCE_RE.match(reference):
        return None
    return name, reference, size


def google_photo_source_url(*, name: Optional[str] = None, reference: Optional[str] = None) -> str:
    """
    A full, key-free Google address for a photo, to record where an imported image came from.

    ``ContentImage.source_url`` must be an absolute URL, so the app-relative proxy path cannot
    be stored there. This one names the same photo without the key.
    """
    if name:
        return _V1_MEDIA_URL.format(name=name)
    return f'{_LEGACY_PHOTO_URL}?{urlencode({"photoreference": reference})}'


def fetch_google_photo(*, name: Optional[str] = None, reference: Optional[str] = None, size: int = DEFAULT_SIZE) -> dict:
    """
    Download one photo from Google and return ``{'content': bytes, 'content_type': str}``.

    Raises ``PhotoError``. Nothing from the Google request (URL, headers, library messages)
    ends up in the error, so the key cannot leak through it.
    """
    api_key = (getattr(settings, 'GOOGLE_MAPS_API_KEY', '') or '').strip()
    if not api_key:
        raise PhotoError('Google Maps is not configured.', 'not_configured', 503)

    try:
        image_url = _resolve_image_url(api_key, name, reference, size)
        image = download_remote_image(image_url, timeout=PHOTO_TIMEOUT)
    except PhotoError:
        raise
    except requests.exceptions.Timeout:
        raise PhotoError('Google took too long to send the photo.', 'upstream_timeout', 504) from None
    except (requests.exceptions.RequestException, ValueError):
        raise PhotoError('The photo could not be loaded.', 'upstream_error', 502) from None

    if image['content_type'] not in SAFE_CONTENT_TYPES:
        raise PhotoError('The photo could not be loaded.', 'upstream_error', 502)
    return image


def _resolve_image_url(api_key: str, name: Optional[str], reference: Optional[str], size: int) -> str:
    """Ask Google where the picture is. The key goes to Google only, never to the image host."""
    if name:
        response = requests.get(
            _V1_MEDIA_URL.format(name=name),
            params={'maxHeightPx': size, 'maxWidthPx': size, 'skipHttpRedirect': 'true'},
            headers={'X-Goog-Api-Key': api_key},
            timeout=PHOTO_TIMEOUT,
        )
        if response.status_code == 404:
            raise PhotoError('That photo was not found.', 'not_found', 404)
        response.raise_for_status()
        photo_uri = (response.json() or {}).get('photoUri')
    else:
        # The legacy API only takes the key as a query parameter. It answers with a redirect to
        # the image host, which is read here rather than followed so the key stays with Google.
        response = requests.get(
            _LEGACY_PHOTO_URL,
            params={'maxwidth': size, 'photoreference': reference, 'key': api_key},
            timeout=PHOTO_TIMEOUT,
            allow_redirects=False,
        )
        if response.status_code == 404:
            raise PhotoError('That photo was not found.', 'not_found', 404)
        if not response.is_redirect:
            response.raise_for_status()
        photo_uri = response.headers.get('Location')

    if not photo_uri:
        raise PhotoError('The photo could not be loaded.', 'upstream_error', 502)
    return photo_uri
