"""Image provenance and GPS metadata helpers for ContentImage."""

from __future__ import annotations

import io
import logging
from typing import Any
from urllib.parse import urlparse

import requests
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from PIL import Image as PILImage
from PIL.ExifTags import GPSTAGS, IFD

from adventures.models import ContentImage
from adventures.utils.geo import make_point, point_to_lat_lon

logger = logging.getLogger(__name__)

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass


class ImageSource:
    UPLOAD = ContentImage.Source.UPLOAD
    GOOGLE = ContentImage.Source.GOOGLE
    WIKIPEDIA = ContentImage.Source.WIKIPEDIA
    URL = ContentImage.Source.URL
    IMMICH = ContentImage.Source.IMMICH


def _hostname_matches_domain(hostname: str, domain: str) -> bool:
    return hostname == domain or hostname.endswith(f'.{domain}')


def infer_source_from_url(url: str) -> str:
    hostname = (urlparse(url).hostname or '').lower()
    if _hostname_matches_domain(hostname, 'googleapis.com') or _hostname_matches_domain(
        hostname, 'googleusercontent.com'
    ):
        return ImageSource.GOOGLE
    if _hostname_matches_domain(hostname, 'wikimedia.org') or _hostname_matches_domain(
        hostname, 'wikipedia.org'
    ):
        return ImageSource.WIKIPEDIA
    return ImageSource.URL


def _normalize_gps_ref(ref) -> str:
    if ref is None:
        return ''
    if isinstance(ref, bytes):
        ref = ref.decode('ascii', errors='ignore')
    return str(ref).strip().upper()[:1]


def _exif_rational_to_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (tuple, list)):
        if len(value) != 2:
            return None
        numerator, denominator = value
        try:
            numerator = float(numerator)
            denominator = float(denominator)
        except (TypeError, ValueError):
            return None
        if denominator == 0:
            return None
        return numerator / denominator
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dms_to_decimal(values, ref) -> float | None:
    if not values or len(values) < 3:
        return None

    degrees = _exif_rational_to_float(values[0])
    minutes = _exif_rational_to_float(values[1])
    seconds = _exif_rational_to_float(values[2])
    if degrees is None or minutes is None or seconds is None:
        return None

    decimal = degrees + minutes / 60 + seconds / 3600
    normalized_ref = _normalize_gps_ref(ref)
    if normalized_ref in ('S', 'W'):
        decimal = -decimal
    return decimal


def extract_gps_from_bytes(content: bytes) -> Point | None:
    try:
        with PILImage.open(io.BytesIO(content)) as img:
            exif = img.getexif()
            if not exif:
                return None

            gps_ifd = exif.get_ifd(IFD.GPSInfo)
            if not gps_ifd:
                return None

            gps_tags = {GPSTAGS.get(key, key): value for key, value in gps_ifd.items()}
            lat = _dms_to_decimal(gps_tags.get('GPSLatitude'), gps_tags.get('GPSLatitudeRef', 'N'))
            lon = _dms_to_decimal(gps_tags.get('GPSLongitude'), gps_tags.get('GPSLongitudeRef', 'E'))
            if lat is None or lon is None:
                return None
            return make_point(lon, lat)
    except Exception:
        logger.debug('Failed to extract GPS from image bytes', exc_info=True)
        return None


def fetch_immich_coordinates(integration, immich_id: str) -> Point | None:
    if not integration or not immich_id:
        return None
    try:
        response = requests.get(
            f'{integration.server_url.rstrip("/")}/assets/{immich_id}',
            headers={'x-api-key': integration.api_key},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        exif_info = payload.get('exifInfo') or {}
        lat = exif_info.get('latitude')
        lon = exif_info.get('longitude')
        if lat is None or lon is None:
            return None
        return make_point(lon, lat)
    except Exception:
        logger.debug('Failed to fetch Immich GPS for asset %s', immich_id, exc_info=True)
        return None


def resolve_image_metadata(
    *,
    file_bytes: bytes | None = None,
    source_url: str | None = None,
    explicit_source: str | None = None,
    immich_id: str | None = None,
    immich_integration=None,
) -> dict[str, Any]:
    source = explicit_source or ImageSource.UPLOAD
    resolved_source_url = source_url

    if immich_id:
        source = ImageSource.IMMICH
    elif source_url and not explicit_source:
        source = infer_source_from_url(source_url)
        resolved_source_url = source_url
    elif source_url:
        resolved_source_url = source_url

    coordinates = None
    if file_bytes:
        coordinates = extract_gps_from_bytes(file_bytes)
    elif immich_id and immich_integration:
        coordinates = fetch_immich_coordinates(immich_integration, immich_id)

    return {
        'source': source,
        'source_url': resolved_source_url,
        'coordinates': coordinates,
    }


def create_content_image(
    *,
    user,
    content_type: ContentType,
    object_id,
    image_file=None,
    immich_id: str | None = None,
    is_primary: bool = False,
    file_bytes: bytes | None = None,
    source_url: str | None = None,
    explicit_source: str | None = None,
    immich_integration=None,
    coordinates: Point | None = None,
) -> ContentImage:
    metadata = resolve_image_metadata(
        file_bytes=file_bytes,
        source_url=source_url,
        explicit_source=explicit_source,
        immich_id=immich_id,
        immich_integration=immich_integration,
    )

    if coordinates is not None:
        metadata['coordinates'] = coordinates

    create_kwargs: dict[str, Any] = {
        'user': user,
        'content_type': content_type,
        'object_id': object_id,
        'is_primary': is_primary,
        'source': metadata['source'],
        'source_url': metadata['source_url'],
        'coordinates': metadata['coordinates'],
    }

    if immich_id:
        create_kwargs['immich_id'] = immich_id
    if image_file is not None:
        create_kwargs['image'] = image_file

    return ContentImage.objects.create(**create_kwargs)


def resolve_coordinates_for_image(image: ContentImage, immich_integration=None):
    """Best-effort GPS lookup for an existing ContentImage record."""
    if image.immich_id:
        return fetch_immich_coordinates(immich_integration, image.immich_id)

    if not image.image:
        return None

    from django.core.files.storage import default_storage

    try:
        with default_storage.open(image.image.name, 'rb') as storage_file:
            return extract_gps_from_bytes(storage_file.read())
    except Exception:
        logger.debug(
            'Failed to read stored image for GPS extraction: %s',
            getattr(image.image, 'name', None),
            exc_info=True,
        )
        return None

