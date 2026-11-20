"""Photos for the printed book, shrunk so a book of many places stays small."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from PIL import Image as PILImage
from PIL import ImageOps
from reportlab.platypus import Image

logger = logging.getLogger(__name__)

THUMB_PX = 480
HERO_PX = 1600


@dataclass(frozen=True)
class Photo:
    data: bytes
    width: int
    height: int

    def flowable(self, width: float, max_height: Optional[float] = None) -> Image:
        """The photo ``width`` points wide, shorter if ``max_height`` would be exceeded."""
        height = width * self.height / self.width
        if max_height and height > max_height:
            height = max_height
            width = height * self.width / self.height
        return Image(io.BytesIO(self.data), width=width, height=height)


def _encode(image: PILImage.Image) -> Photo:
    image = image.convert('RGB')
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=80, optimize=True)
    return Photo(buffer.getvalue(), image.width, image.height)


class MediaCache:
    """Loads and shrinks the photos of one book. With ``enabled`` off every lookup answers None."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._cache: Dict[Any, Optional[Photo]] = {}

    @staticmethod
    def _stored_image(obj):
        """The best uploaded image of a record: its primary one, else the first with a file."""
        images = [i for i in obj.images.all() if i.image]
        if not images:
            return None
        return next((i for i in images if i.is_primary), images[0])

    def _load(self, content_image, key: Any, size: int, crop: Optional[tuple[float, float]] = None) -> Optional[Photo]:
        if key in self._cache:
            return self._cache[key]
        photo = None
        try:
            with content_image.image.open('rb') as fh, PILImage.open(fh) as source:
                source = ImageOps.exif_transpose(source)
                if crop:
                    # Fill a box of this width:height ratio, cutting the overflow off the edges.
                    box_w = size
                    box_h = max(int(size * crop[1] / crop[0]), 1)
                    fitted = ImageOps.fit(source.convert('RGB'), (box_w, box_h), PILImage.LANCZOS)
                    photo = _encode(fitted)
                    fitted.close()
                else:
                    source.thumbnail((size, size), PILImage.LANCZOS)
                    photo = _encode(source)
        except Exception:  # noqa: BLE001 - a missing or broken file just means no photo
            logger.warning('Could not read image %s for the PDF', getattr(content_image, 'pk', '?'), exc_info=True)
        self._cache[key] = photo
        return photo

    def thumbnail(self, obj) -> Optional[Photo]:
        """A small photo of a place or stay, or None."""
        if not self.enabled or getattr(obj, '_story_hide_photos', False):
            return None
        image = self._stored_image(obj)
        return self._load(image, ('thumb', image.pk), THUMB_PX) if image else None

    def cover(self, collection, width: float, height: float) -> Optional[Photo]:
        """The cover photo cropped to ``width`` x ``height`` (points), or None."""
        if not self.enabled:
            return None
        image = collection.primary_image
        if not image or not image.image:
            return None
        return self._load(image, ('cover', image.pk, round(width), round(height)), HERO_PX, crop=(width, height))
