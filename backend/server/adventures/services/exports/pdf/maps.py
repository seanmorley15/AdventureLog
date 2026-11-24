"""
Maps for the printed book: a few pins and a route drawn on a basemap.

The basemap comes from a tile server (``PDF_MAP_TILE_URL``). While one book is made, a tile
that cannot be fetched, or running out of time, switches every later map to a plain
drawing (grid and scale bar), so a slow or blocked tile server costs seconds, not minutes.
"""

from __future__ import annotations

import io
import logging
import math
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Optional, Sequence, Tuple

import requests
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

TILE_SIZE = 256
# Pixels per point in the picture: sharp enough for print without huge files.
PRINT_SCALE = 2
MAX_TILES = 36
MAX_ZOOM = 17
TILE_TIMEOUT = 5
# Seconds a whole book may spend fetching tiles before the rest of the maps are drawn plain.
TILE_BUDGET = 25
USER_AGENT = 'AdventureLog/pdf-export (self-hosted travel planner)'

BACKGROUND = (238, 243, 242)
GRID = (214, 224, 222)
ROUTE = (15, 23, 42)


@dataclass(frozen=True)
class MapPoint:
    lat: float
    lon: float
    label: str = ''
    color: str = '#0d9488'


@dataclass(frozen=True)
class MapLeg:
    """A line between two places. Transport is dashed; the order of stops is solid."""
    start: Tuple[float, float]  # (lat, lon)
    end: Tuple[float, float]
    dashed: bool = False


def world_pixel(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    """Web Mercator: the position of a point on the whole world at ``zoom``, in 256px tiles."""
    lat = max(-85.0511, min(85.0511, lat))
    scale = TILE_SIZE * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * scale
    siny = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) * scale
    return x, y


def choose_view(points: Sequence[Tuple[float, float]], width: float, height: float, padding: float = 36) -> Tuple[int, float, float]:
    """
    The zoom and the world-pixel centre that fit ``points`` (lat, lon) in a ``width`` x ``height``
    picture with ``padding`` around them. A single point, or points on top of each other, get a
    street-level zoom.
    """
    if not points:
        raise ValueError('No points to fit')
    inner_w = max(width - 2 * padding, 1)
    inner_h = max(height - 2 * padding, 1)
    for zoom in range(MAX_ZOOM, 0, -1):
        xs, ys = zip(*(world_pixel(lat, lon, zoom) for lat, lon in points))
        if max(xs) - min(xs) <= inner_w and max(ys) - min(ys) <= inner_h:
            if len(set(points)) == 1:
                zoom = min(zoom, 14)
                xs, ys = zip(*(world_pixel(lat, lon, zoom) for lat, lon in points))
            return zoom, (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    xs, ys = zip(*(world_pixel(lat, lon, 1) for lat, lon in points))
    return 1, (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


_session: Optional[requests.Session] = None


def fetch_tile(url_template: str, zoom: int, x: int, y: int) -> Image.Image:
    """One tile as an image. Raises when it cannot be had (tests replace this)."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers['User-Agent'] = USER_AGENT
    wrap = 2 ** zoom
    url = url_template.format(z=zoom, x=x % wrap, y=y)
    response = _session.get(url, timeout=TILE_TIMEOUT)
    response.raise_for_status()
    with Image.open(io.BytesIO(response.content)) as tile:
        return tile.convert('RGB')


@lru_cache(maxsize=4)
def _font(size: int, bold: bool) -> ImageFont.ImageFont:
    from .fonts import BOLD_FONT, _SYSTEM_FONT_CANDIDATES, BODY_FONT  # noqa: PLC0415

    for path in _SYSTEM_FONT_CANDIDATES[BOLD_FONT if bold else BODY_FONT]:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _nice_distance(max_meters: float) -> float:
    exponent = 10 ** math.floor(math.log10(max_meters))
    for step in (5, 2, 1):
        if step * exponent <= max_meters:
            return step * exponent
    return exponent


def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = value.lstrip('#')
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


class MapRenderer:
    """Draws maps for one book. Make one per PDF so fetched tiles and the time budget are shared."""

    def __init__(self):
        self.url_template: str = getattr(settings, 'PDF_MAP_TILE_URL', '')
        self.attribution: str = getattr(settings, 'PDF_MAP_ATTRIBUTION', '')
        self.tiles_enabled: bool = bool(getattr(settings, 'PDF_MAP_TILES', True)) and bool(self.url_template)
        # Retina tiles (512px) already hold twice the detail. Plain 256px tiles are fetched one
        # zoom deeper so the printed map is just as sharp (the map labels come out smaller).
        self.retina: bool = '@2x' in self.url_template
        self._cache: Dict[Tuple[int, int, int], Optional[Image.Image]] = {}
        self._rendered: Dict[tuple, bytes] = {}
        self._started = time.monotonic()
        self.used_tiles = False

    def _tile(self, zoom: int, x: int, y: int) -> Optional[Image.Image]:
        key = (zoom, x, y)
        if key in self._cache:
            return self._cache[key]
        tile = None
        if 0 <= y < 2 ** zoom and self.tiles_enabled:
            if time.monotonic() - self._started > TILE_BUDGET:
                logger.info('PDF map tile budget used up; drawing maps without a basemap')
                self.tiles_enabled = False
            else:
                try:
                    tile = fetch_tile(self.url_template, zoom, x, y)
                except Exception as exc:  # noqa: BLE001 - any failure means "no basemap"
                    logger.warning('PDF map tile %s/%s/%s could not be fetched (%s); drawing maps without a basemap', zoom, x, y, exc)
                    self.tiles_enabled = False
        self._cache[key] = tile
        return tile

    def render(
        self,
        points: Sequence[MapPoint],
        width: float,
        height: float,
        legs: Sequence[MapLeg] = (),
    ) -> Optional[bytes]:
        """JPEG bytes of a ``width`` x ``height`` (points) map showing ``points``, or None if there is nothing to show."""
        if not points:
            return None
        # A book is laid out more than once; draw each map only the first time.
        key = (tuple(points), tuple(legs), round(width), round(height))
        if key in self._rendered:
            return self._rendered[key]
        coords = [(p.lat, p.lon) for p in points]
        for leg in legs:
            coords.extend([leg.start, leg.end])
        zoom, cx, cy = choose_view(coords, width, height)
        # Fewer tiles than the cap: zoom out until the picture needs MAX_TILES or fewer.
        while zoom > 1 and self._tile_count(zoom, cx, cy, width, height) > MAX_TILES:
            zoom -= 1
            cx, cy = cx / 2, cy / 2

        s = PRINT_SCALE
        px_w, px_h = int(width * s), int(height * s)
        left, top = cx - width / 2, cy - height / 2  # world px (256-tile units) at the picture's corner
        image = Image.new('RGB', (px_w, px_h), BACKGROUND)

        have_basemap = self._paint_tiles(image, zoom, left, top, width, height, s)
        if not have_basemap:
            self._paint_plain(image, zoom, left, top, s)
        draw = ImageDraw.Draw(image)

        def to_px(lat: float, lon: float) -> Tuple[float, float]:
            x, y = world_pixel(lat, lon, zoom)
            return (x - left) * s, (y - top) * s

        self._draw_legs(draw, legs, to_px, s)
        self._draw_pins(draw, points, to_px, s)
        self._draw_credit(draw, px_w, px_h, s, have_basemap)

        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=82, optimize=True)
        image.close()
        self._rendered[key] = buffer.getvalue()
        return self._rendered[key]

    # -- pieces ---------------------------------------------------------------------------------

    @property
    def _unit(self) -> float:
        """How much of the map one tile covers, in the picture's units (points)."""
        return TILE_SIZE if self.retina else TILE_SIZE / 2

    @property
    def _extra_zoom(self) -> int:
        return 0 if self.retina else 1

    def _tile_range(self, cx: float, cy: float, width: float, height: float):
        left, top = cx - width / 2, cy - height / 2
        unit = self._unit
        return (
            int(math.floor(left / unit)), int(math.floor((left + width) / unit)),
            int(math.floor(top / unit)), int(math.floor((top + height) / unit)),
        )

    def _tile_count(self, zoom: int, cx: float, cy: float, width: float, height: float) -> int:
        x0, x1, y0, y1 = self._tile_range(cx, cy, width, height)
        return (x1 - x0 + 1) * (y1 - y0 + 1)

    def _paint_tiles(self, image: Image.Image, zoom: int, left: float, top: float, width: float, height: float, s: int) -> bool:
        if not self.tiles_enabled:
            return False
        x0, x1, y0, y1 = self._tile_range(left + width / 2, top + height / 2, width, height)
        fetch_zoom = zoom + self._extra_zoom
        tiles = []
        for tx in range(x0, x1 + 1):
            for ty in range(y0, y1 + 1):
                tile = self._tile(fetch_zoom, tx, ty)
                if tile is None:
                    # A map half in tiles and half blank is worse than a plain one.
                    return False
                tiles.append((tx, ty, tile))
        unit = self._unit
        size = round(unit * s)
        for tx, ty, tile in tiles:
            resized = tile if tile.size == (size, size) else tile.resize((size, size), Image.LANCZOS)
            image.paste(resized, (round((tx * unit - left) * s), round((ty * unit - top) * s)))
        self.used_tiles = True
        return True

    def _paint_plain(self, image: Image.Image, zoom: int, left: float, top: float, s: int) -> None:
        """Background, a lat/lon grid, and a scale bar - the map when there is no basemap."""
        draw = ImageDraw.Draw(image)
        w, h = image.size
        right, bottom = left + w / s, top + h / s
        # Degrees between grid lines: about one every 90 points.
        scale = TILE_SIZE * (2 ** zoom)
        deg_per_px = 360.0 / scale
        target = deg_per_px * 90
        step = next((d for d in (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 45) if d >= target), 45)
        lon_left = left / scale * 360 - 180
        lon_right = right / scale * 360 - 180
        lon = math.floor(lon_left / step) * step
        while lon <= lon_right:
            x = ((lon + 180) / 360 * scale - left) * s
            draw.line([(x, 0), (x, h)], fill=GRID, width=max(1, s))
            lon += step
        lat_top = self._lat_from_world_y(top, scale)
        lat_bottom = self._lat_from_world_y(bottom, scale)
        lat = math.floor(lat_bottom / step) * step
        while lat <= lat_top:
            _, y = world_pixel(lat, 0, zoom)
            draw.line([(0, (y - top) * s), (w, (y - top) * s)], fill=GRID, width=max(1, s))
            lat += step

        mid_lat = self._lat_from_world_y((top + bottom) / 2, scale)
        meters_per_px = 156543.03392 * math.cos(math.radians(mid_lat)) / (2 ** zoom) * (TILE_SIZE / 256)
        bar_m = _nice_distance(meters_per_px * 110)
        bar_px = bar_m / meters_per_px * s
        label = f'{bar_m / 1000:g} km' if bar_m >= 1000 else f'{bar_m:g} m'
        x0, y0 = 14 * s, h - 22 * s
        draw.rectangle([x0, y0, x0 + bar_px, y0 + 3 * s], fill=ROUTE)
        draw.text((x0, y0 - 14 * s), label, fill=ROUTE, font=_font(9 * s, True))

    @staticmethod
    def _lat_from_world_y(y: float, scale: float) -> float:
        n = math.pi - 2 * math.pi * y / scale
        return math.degrees(math.atan(math.sinh(n)))

    @staticmethod
    def _draw_legs(draw: ImageDraw.ImageDraw, legs, to_px, s: int) -> None:
        for leg in legs:
            a, b = to_px(*leg.start), to_px(*leg.end)
            if not leg.dashed:
                draw.line([a, b], fill=ROUTE, width=2 * s)
                continue
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            if length < 1:
                continue
            dash, gap = 9 * s, 6 * s
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            pos = 0.0
            while pos < length:
                end = min(pos + dash, length)
                draw.line([(a[0] + ux * pos, a[1] + uy * pos), (a[0] + ux * end, a[1] + uy * end)], fill=ROUTE, width=2 * s)
                pos += dash + gap

    @staticmethod
    def _draw_pins(draw: ImageDraw.ImageDraw, points: Sequence[MapPoint], to_px, s: int) -> None:
        radius = 10 * s
        for point in points:
            x, y = to_px(point.lat, point.lon)
            draw.ellipse([x - radius - 2 * s, y - radius - 2 * s, x + radius + 2 * s, y + radius + 2 * s], fill=(255, 255, 255))
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=_hex_to_rgb(point.color))
            if point.label:
                font = _font(int((11 if len(point.label) < 3 else 9) * s), True)
                draw.text((x, y), point.label, fill=(255, 255, 255), font=font, anchor='mm')

    def _draw_credit(self, draw: ImageDraw.ImageDraw, w: int, h: int, s: int, have_basemap: bool) -> None:
        text = self.attribution if have_basemap else 'No basemap - offline drawing'
        if not text:
            return
        font = _font(7 * s, False)
        box = draw.textbbox((0, 0), text, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        pad = 3 * s
        draw.rectangle([w - tw - 2 * pad, h - th - 2 * pad, w, h], fill=(255, 255, 255))
        draw.text((w - tw - pad, h - th - pad - box[1]), text, fill=(71, 85, 105), font=font)
