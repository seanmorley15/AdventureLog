"""Field-level conversion between records and the JSON of a backup, shared by export and restore."""

import re
from decimal import Decimal, InvalidOperation

from core.geo import point_to_lat_lon
from worldtravel.models import Country


def iso(value):
    return value.isoformat() if value else None


def storage_basename(name):
    return name.split('/')[-1]


def float_or_none(value):
    # Zero is a real value (a flat climb, a free night), not a missing one.
    return float(value) if value is not None else None


def seconds_or_none(duration):
    return duration.total_seconds() if duration is not None else None


def lat_lon_strings(point):
    """(latitude, longitude) as strings, or (None, None). The format locations, transport and lodging use."""
    lat, lon = point_to_lat_lon(point)
    return (str(lat) if lat is not None else None, str(lon) if lon is not None else None)


def lat_lon_floats(point):
    lat, lon = point_to_lat_lon(point)
    return (float(lat) if lat is not None else None, float(lon) if lon is not None else None)


def money_fields(money):
    """(amount, currency) as strings, or (None, None)."""
    if money is None:
        return None, None
    return str(money.amount), str(money.currency)


def optional_str(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def serialize_images(images):
    """Describe a ContentImage queryset or related manager. The files travel in the archive."""
    serialized = []
    for image in images.all():
        lat, lon = point_to_lat_lon(image.coordinates)
        entry = {
            'immich_id': image.immich_id,
            'is_primary': image.is_primary,
            'source': image.source,
            'source_url': image.source_url,
            'latitude': lat,
            'longitude': lon,
            'filename': None,
        }
        if image.image:
            entry['filename'] = storage_basename(image.image.name)
        serialized.append(entry)
    return serialized


def serialize_attachments(attachments):
    serialized = []
    for attachment in attachments.all():
        entry = {'name': attachment.name, 'filename': None}
        if attachment.file:
            entry['filename'] = storage_basename(attachment.file.name)
        serialized.append(entry)
    return serialized


def serialize_trail(trail):
    """A trail on a place. Author fields are optional so older backups stay readable."""
    data = {
        'name': trail.name,
        'link': trail.link,
        'wanderer_id': trail.wanderer_id,
        'created_at': trail.created_at.isoformat() if trail.created_at else None,
        'images': serialize_images(trail.images),
    }
    username = getattr(trail, 'wanderer_author_username', None)
    domain = getattr(trail, 'wanderer_author_domain', None)
    if username:
        data['wanderer_author_username'] = username
    if domain:
        data['wanderer_author_domain'] = domain
    return data


def parse_trail(trail_data):
    """
    Read a trail from a backup, or None if it cannot be restored. Old backups only have
    name/link/wanderer_id; author username/domain are backfilled on read when missing.
    """
    if not isinstance(trail_data, dict):
        return None

    name = optional_str(trail_data.get('name'))
    if not name:
        return None

    link = optional_str(trail_data.get('link'))
    wanderer_id = optional_str(trail_data.get('wanderer_id'))
    if not link and not wanderer_id:
        return None

    domain = optional_str(trail_data.get('wanderer_author_domain'))
    if domain:
        domain = domain.lstrip('@')

    return {
        'name': name,
        'link': link,
        'wanderer_id': wanderer_id,
        'wanderer_author_username': optional_str(trail_data.get('wanderer_author_username')),
        'wanderer_author_domain': domain,
        'created_at': trail_data.get('created_at'),
    }


def normalize_money_amount(value):
    """A Decimal from legacy or canonical backup values, or None."""
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    # Accept values like "$1,553.59" and "USD 1,553.59".
    cleaned = re.sub(r'[^0-9,\.\-]', '', text)
    if not cleaned:
        return None

    if ',' in cleaned and '.' in cleaned:
        if cleaned.rfind(',') > cleaned.rfind('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[-1]) in (1, 2):
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_money(value, currency=None, default_currency='USD'):
    """A backup money value as schema-safe (amount, currency)."""
    parsed_currency = currency
    parsed_value = value

    if isinstance(value, dict):
        parsed_value = value.get('amount')
        parsed_currency = parsed_currency or value.get('currency')

    amount = normalize_money_amount(parsed_value)
    if amount is None:
        # django-money stores currency in a separate non-null column even when the amount
        # itself is empty, so a blank legacy value still needs a default currency.
        return None, default_currency

    normalized_currency = parsed_currency or default_currency
    if isinstance(normalized_currency, str):
        normalized_currency = normalized_currency.strip().upper() or default_currency
    else:
        normalized_currency = default_currency

    return amount, normalized_currency


def resolve_import_country(data, region=None):
    """
    Resolve a location's Country without trusting raw Country PKs.

    Country.id is an auto-increment integer that differs between installs (it depends on the
    order the countries dataset was loaded), so a PK from a backup can silently point at a
    different country (e.g. Germany -> Ghana). Stable identifiers are used instead, in order
    of reliability:
      1. the resolved region's country (region IDs are ISO 3166-2 strings),
      2. the exported ISO 3166-1 alpha-2 ``country_code``,
      3. legacy backups only: the raw Country PK, as a last resort.
    """
    if region is not None and region.country_id:
        return region.country

    country_code = data.get('country_code')
    if isinstance(country_code, str) and country_code.strip():
        country = Country.objects.filter(country_code=country_code.strip().upper()).first()
        if country:
            return country

    # Legacy backups (no country_code): fall back to the city's/region's ISO prefix before
    # trusting the raw PK.
    for key in ('region', 'city'):
        ref = data.get(key)
        if isinstance(ref, str) and '-' in ref:
            country = Country.objects.filter(country_code=ref.split('-', 1)[0].upper()).first()
            if country:
                return country

    legacy_id = data.get('country')
    if legacy_id:
        return Country.objects.filter(id=legacy_id).first()
    return None
