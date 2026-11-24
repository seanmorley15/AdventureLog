"""What the person asked for when they exported: paper, photos and write-in space."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from reportlab.lib.pagesizes import A4, letter

PAPER_SIZES = {'a4': A4, 'letter': letter}


@dataclass(frozen=True)
class PdfOptions:
    paper: str = 'a4'
    photos: bool = True
    # Ruled lines and blanks to write in. On for folders (a workbook), off for trips.
    journal: bool = False

    @property
    def pagesize(self) -> tuple[float, float]:
        return PAPER_SIZES[self.paper]

    @classmethod
    def from_params(
        cls, params: Optional[Mapping[str, Any]] = None, *, user=None, collection=None
    ) -> 'PdfOptions':
        """
        Options from what was sent (only the keys the person set), with the rest filled in:
        Letter for people on imperial units, and write-in space for folders.
        """
        params = params or {}
        paper = params.get('paper')
        if paper not in PAPER_SIZES:
            imperial = getattr(user, 'measurement_system', None) == 'imperial'
            paper = 'letter' if imperial else 'a4'
        journal = params.get('journal')
        if journal is None:
            journal = getattr(collection, 'type', None) == 'folder'
        photos = params.get('photos')
        return cls(paper=paper, photos=True if photos is None else bool(photos), journal=bool(journal))
