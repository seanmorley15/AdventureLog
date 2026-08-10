"""
Build branded PNG share cards for collections and locations (social media).
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple, Union

import qrcode
from django.db.models import Prefetch
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from adventures.models import Collection, ContentImage, Location, Visit
from adventures.services.collection_pdf import get_collection_for_pdf

ASPECTS: dict[str, Tuple[int, int]] = {
    'square': (1080, 1080),
    'story': (1080, 1920),
    'landscape': (1200, 628),
}

COLOR_PRIMARY = (13, 148, 136)
COLOR_MUTED = (100, 116, 139)
COLOR_LIGHT = (248, 250, 252)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK = (15, 23, 42)

_BUNDLED_DIR = Path(__file__).resolve().parent.parent / 'pdf_assets' / 'fonts'
_FONT_CANDIDATES = [
    _BUNDLED_DIR / 'NotoSans-Regular.ttf',
    Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'),
    Path('/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf'),
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
]
_BOLD_CANDIDATES = [
    _BUNDLED_DIR / 'NotoSans-Bold.ttf',
    Path('/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf'),
    Path('/usr/share/fonts/opentype/noto/NotoSans-Bold.ttf'),
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
]


def valid_aspect(aspect: str) -> bool:
    return aspect in ASPECTS


def aspect_dimensions(aspect: str) -> Tuple[int, int]:
    if aspect not in ASPECTS:
        raise ValueError(f'Invalid aspect: {aspect}')
    return ASPECTS[aspect]


@lru_cache(maxsize=1)
def _body_font_path() -> Optional[Path]:
    return next((p for p in _FONT_CANDIDATES if p.is_file()), None)


@lru_cache(maxsize=1)
def _bold_font_path() -> Optional[Path]:
    return next((p for p in _BOLD_CANDIDATES if p.is_file()), None)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = (_bold_font_path() if bold else _body_font_path())
    if path:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            pass
    return ImageFont.load_default()


def _format_short_date(d: Optional[date]) -> str:
    if not d:
        return ''
    return d.strftime('%b %d, %Y')


def _format_date_range(start: Optional[date], end: Optional[date]) -> str:
    if start and end:
        if start == end:
            return _format_short_date(start)
        if start.year == end.year:
            return f'{start.strftime("%b %d")} – {end.strftime("%b %d, %Y")}'
        return f'{_format_short_date(start)} – {_format_short_date(end)}'
    if start:
        return f'From {_format_short_date(start)}'
    if end:
        return f'Until {_format_short_date(end)}'
    return ''


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _truncate_to_width(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int
) -> str:
    if not text:
        return ''
    if _text_width(draw, text, font) <= max_width:
        return text
    ellipsis = '...'
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = text[:mid].rstrip() + ellipsis
        if _text_width(draw, candidate, font) <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + ellipsis if low > 0 else ellipsis


def _open_image_field(image_field) -> Optional[PILImage.Image]:
    if not image_field:
        return None
    try:
        with image_field.open('rb') as fh:
            img = PILImage.open(fh)
            return img.convert('RGB')
    except Exception:
        return None


def _location_hero_image(location: Location) -> Optional[PILImage.Image]:
    images = sorted(location.images.all(), key=lambda img: (not img.is_primary,))
    if not images:
        return None
    for img in images:
        if img.image:
            opened = _open_image_field(img.image)
            if opened:
                return opened
    return None


def _collection_hero_image(collection: Collection) -> Optional[PILImage.Image]:
    if collection.primary_image and collection.primary_image.image:
        return _open_image_field(collection.primary_image.image)
    for loc in collection.locations.all():
        hero = _location_hero_image(loc)
        if hero:
            return hero
    return None


def _cover_crop(img: PILImage.Image, width: int, height: int) -> PILImage.Image:
    target_ratio = width / height
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        cropped = img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        cropped = img.crop((0, top, src_w, top + new_h))
    return cropped.resize((width, height), PILImage.Resampling.LANCZOS)


def _gradient_background(width: int, height: int) -> PILImage.Image:
    base = PILImage.new('RGB', (width, height), COLOR_PRIMARY)
    overlay = PILImage.new('RGBA', (width, height))
    draw = ImageDraw.Draw(overlay)
    for y in range(height):
        alpha = int(180 * (y / max(height - 1, 1)))
        draw.line([(0, y), (width, y)], fill=(15, 118, 110, alpha))
    return PILImage.alpha_composite(base.convert('RGBA'), overlay).convert('RGB')


def _apply_bottom_gradient(canvas: PILImage.Image, start_ratio: float = 0.35) -> PILImage.Image:
    width, height = canvas.size
    overlay = PILImage.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    start_y = int(height * start_ratio)
    for y in range(start_y, height):
        progress = (y - start_y) / max(height - start_y - 1, 1)
        alpha = int(210 * progress)
        draw.line([(0, y), (width, y)], fill=(15, 23, 42, alpha))
    return PILImage.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')


def _make_qr(url: str, outer_size: int) -> PILImage.Image:
    """
    Standard black-on-white QR with quiet zone, then a white mat for dark backgrounds.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    core = qr.make_image(fill_color='black', back_color='white').convert('RGB')

    # Extra white mat so the code stays scannable on gradient/dark footers
    mat_px = max(12, outer_size // 12)
    matted = PILImage.new(
        'RGB',
        (core.width + 2 * mat_px, core.height + 2 * mat_px),
        COLOR_WHITE,
    )
    matted.paste(core, (mat_px, mat_px))
    return matted.resize((outer_size, outer_size), PILImage.Resampling.LANCZOS)


def _draw_footer(
    canvas: PILImage.Image,
    width: int,
    height: int,
    username: str,
    public_url: str,
    padding: int,
    qr_size: int,
) -> None:
    draw = ImageDraw.Draw(canvas)
    brand_font = _load_font(28, bold=True)
    user_font = _load_font(22)
    footer_y = height - padding - qr_size

    draw.text((padding, footer_y + 8), 'AdventureLog', font=brand_font, fill=COLOR_PRIMARY)
    if username:
        draw.text((padding, footer_y + 40), f'@{username}', font=user_font, fill=COLOR_WHITE)

    qr = _make_qr(public_url, qr_size)
    canvas.paste(qr, (width - padding - qr_size, footer_y))


def _compose_card(
    *,
    width: int,
    height: int,
    hero: Optional[PILImage.Image],
    title: str,
    subtitle: str,
    stats: str,
    username: str,
    public_url: str,
    highlights: Optional[list[str]] = None,
) -> bytes:
    padding = max(48, width // 22)
    if hero:
        canvas = _cover_crop(hero, width, height)
        canvas = _apply_bottom_gradient(canvas, start_ratio=0.3 if height > width else 0.45)
    else:
        canvas = _gradient_background(width, height)

    draw = ImageDraw.Draw(canvas)

    title_size = 72 if height >= 1500 else (56 if width >= 1000 else 48)
    subtitle_size = 32 if height >= 1500 else 26
    stats_size = 24 if height >= 1500 else 22
    highlight_size = 22

    title_font = _load_font(title_size, bold=True)
    subtitle_font = _load_font(subtitle_size)
    stats_font = _load_font(stats_size)
    highlight_font = _load_font(highlight_size)

    content_width = width - 2 * padding
    # Large enough to scan from a phone screen; scales with card size
    qr_size = max(120, min(160, width // 7))
    text_bottom = height - padding - qr_size - 16

    lines: list[tuple[str, ImageFont.ImageFont, Tuple[int, int, int]]] = []
    y = text_bottom

    if highlights:
        for name in reversed(highlights[:3]):
            line = f'• {_truncate_to_width(draw, name, highlight_font, content_width - 24)}'
            lines.append((line, highlight_font, COLOR_LIGHT))
    if stats:
        lines.append((_truncate_to_width(draw, stats, stats_font, content_width), stats_font, COLOR_LIGHT))
    if subtitle:
        lines.append((_truncate_to_width(draw, subtitle, subtitle_font, content_width), subtitle_font, COLOR_LIGHT))
    title_line = _truncate_to_width(draw, title, title_font, content_width)
    lines.append((title_line, title_font, COLOR_WHITE))

    for text, font, color in lines:
        bbox = draw.textbbox((0, 0), text, font=font)
        line_h = bbox[3] - bbox[1]
        y -= line_h + 12
        draw.text((padding, y), text, font=font, fill=color)

    _draw_footer(canvas, width, height, username, public_url, padding, qr_size)

    buf = io.BytesIO()
    canvas.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def get_location_for_share(location_id) -> Location:
    return (
        Location.objects.filter(pk=location_id)
        .select_related('user', 'city', 'region', 'country', 'category')
        .prefetch_related('images', Prefetch('visits', queryset=Visit.objects.order_by('start_date')))
        .get()
    )


def _location_place_name(location: Location) -> str:
    parts = []
    if location.city:
        parts.append(location.city.name)
    elif location.region:
        parts.append(location.region.name)
    if location.country:
        parts.append(location.country.name)
    if parts:
        return ', '.join(parts)
    return location.location or ''


def _location_visit_range(location: Location) -> str:
    visits = list(location.visits.all())
    if not visits:
        return ''
    starts = [v.start_date for v in visits if v.start_date]
    ends = [v.end_date for v in visits if v.end_date]
    if not starts:
        return ''
    start = min(starts).date() if isinstance(min(starts), datetime) else min(starts)
    end = max(ends).date() if ends and isinstance(max(ends), datetime) else (max(ends) if ends else None)
    return _format_date_range(start, end)


def build_location_share_image(location: Location, aspect: str, public_url: str) -> bytes:
    width, height = aspect_dimensions(aspect)
    hero = _location_hero_image(location)
    place = _location_place_name(location)
    visit_range = _location_visit_range(location)

    subtitle_parts = [p for p in [place, visit_range] if p]
    subtitle = ' · '.join(subtitle_parts)

    stats_parts = []
    if location.rating is not None:
        stats_parts.append(f'★ {location.rating:g}')
    if location.tags:
        stats_parts.append(' · '.join(location.tags[:3]))
    stats = ' · '.join(stats_parts)

    username = getattr(location.user, 'username', '') or ''

    return _compose_card(
        width=width,
        height=height,
        hero=hero,
        title=location.name,
        subtitle=subtitle,
        stats=stats,
        username=username,
        public_url=public_url,
    )


def build_collection_share_image(collection: Collection, aspect: str, public_url: str) -> bytes:
    width, height = aspect_dimensions(aspect)
    hero = _collection_hero_image(collection)
    date_range = _format_date_range(collection.start_date, collection.end_date)
    loc_count = collection.locations.count()
    loc_label = 'location' if loc_count == 1 else 'locations'

    subtitle = date_range
    stats = f'{loc_count} {loc_label}' if loc_count else ''

    top_locations = list(collection.locations.all()[:3])
    highlights = [loc.name for loc in top_locations]

    username = getattr(collection.user, 'username', '') or ''

    return _compose_card(
        width=width,
        height=height,
        hero=hero,
        title=collection.name,
        subtitle=subtitle,
        stats=stats,
        username=username,
        public_url=public_url,
        highlights=highlights if highlights else None,
    )


def build_share_image(
    obj: Union[Collection, Location], aspect: str, public_url: str
) -> bytes:
    if isinstance(obj, Collection):
        return build_collection_share_image(obj, aspect, public_url)
    if isinstance(obj, Location):
        return build_location_share_image(obj, aspect, public_url)
    raise TypeError(f'Unsupported object type: {type(obj)}')


def share_image_filename(obj: Union[Collection, Location], aspect: str) -> str:
    safe_name = re.sub(r'[^\w\s-]', '', obj.name).strip().replace(' ', '_') or 'share'
    kind = 'collection' if isinstance(obj, Collection) else 'location'
    return f'{safe_name}_{kind}_{aspect}.png'


def resolve_share_page_url(request, path: str) -> str:
    """
    Build an absolute URL encoded in share-card QR codes.
    Prefer the browser Origin/Referer (frontend) over backend PUBLIC_URL.
    """
    from django.conf import settings
    from urllib.parse import urlparse

    if not path.startswith('/'):
        path = f'/{path}'

    for header in ('Origin', 'Referer'):
        raw = request.headers.get(header)
        if not raw:
            continue
        parsed = urlparse(raw)
        if parsed.scheme and parsed.netloc:
            return f'{parsed.scheme}://{parsed.netloc}{path}'

    base = getattr(settings, 'PUBLIC_URL', 'http://localhost:8000').rstrip('/')
    return f'{base}{path}'


def get_collection_for_share(collection_id) -> Collection:
    return get_collection_for_pdf(collection_id)
