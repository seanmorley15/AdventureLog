"""Choosing the book: a trip gets a Trip Book, a folder gets a Field Guide."""

from __future__ import annotations

import re
from typing import Optional

from adventures.models import Collection

from .data import apply_story_groups
from .folder import build_field_guide
from .options import PdfOptions
from .trip import build_trip_book


def build_collection_pdf(collection: Collection, story: bool = False, options: Optional[PdfOptions] = None) -> bytes:
    """
    Return PDF bytes for the given collection.

    Members get the full plan, including prices and confirmation numbers.
    ``story=True`` is the public reader's copy and follows the story groups.
    """
    options = options or PdfOptions.from_params(None, collection=collection)
    if story:
        apply_story_groups(collection)
    if collection.type == Collection.Type.TRIP:
        return build_trip_book(collection, options, story)
    return build_field_guide(collection, options, story)


def pdf_filename_for_collection(collection: Collection) -> str:
    raw = (collection.name or 'collection').strip()
    safe = re.sub(r'[^\w\s-]', '', raw, flags=re.UNICODE)
    safe = re.sub(r'[-\s]+', '_', safe).strip('_') or 'collection'
    suffix = 'trip_book' if collection.type == Collection.Type.TRIP else 'field_guide'
    return f'{safe}_{suffix}.pdf'
