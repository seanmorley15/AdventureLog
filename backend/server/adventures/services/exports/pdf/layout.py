"""The document: cover and body pages, running footer, bookmarks, and page references."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, PageTemplate

from adventures.models import Collection

from .fonts import bold_font_name, ensure_pdf_fonts
from .maps import MapRenderer
from .media import MediaCache, Photo
from .options import PdfOptions
from .theme import COLOR_FAINT, COLOR_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_DARK

MARGIN = 40
HERO_HEIGHT = 300
TOP_MARGIN = 56
BOTTOM_MARGIN = 50


@dataclass
class Ctx:
    """What every part of a book needs while it is built."""

    collection: Collection
    options: PdfOptions
    story: bool
    styles: dict
    width: float
    media: MediaCache
    maps: MapRenderer
    # Page numbers found by the previous pass (anchor key -> page) and the book's length.
    refs: Dict[str, int] = field(default_factory=dict)
    total_pages: int = 0

    @property
    def show_visits(self) -> bool:
        # Visits are the place's own log and are not part of a published story.
        return not self.story

    def page_of(self, key: str) -> str:
        page = self.refs.get(key)
        return str(page) if page else '–'


class Anchor(Flowable):
    """A spot in the book other parts can link to, and an entry in the PDF's outline."""

    def __init__(self, key: str, title: Optional[str] = None, level: int = 0):
        super().__init__()
        self.anchor_key = key
        self.outline_title = title
        self.outline_level = level

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        pass


class EndMarker(Flowable):
    """Last in the story: tells the document how many pages it has."""

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        pass


class BookDoc(BaseDocTemplate):
    def __init__(
        self,
        buffer,
        options: PdfOptions,
        *,
        title: str,
        kind_label: str,
        footer_text: str,
        hero: Optional[Photo],
        total_pages: int,
    ):
        width, height = options.pagesize
        super().__init__(
            buffer,
            pagesize=(width, height),
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=TOP_MARGIN,
            bottomMargin=BOTTOM_MARGIN,
            title=title,
            author='AdventureLog',
        )
        self.kind_label = kind_label
        self.footer_text = footer_text
        self.hero = hero
        self.total_pages = total_pages
        self.page_refs: Dict[str, int] = {}
        self.last_page = 0
        content_w = width - 2 * MARGIN
        cover = Frame(MARGIN, 48, content_w, height - HERO_HEIGHT - 48 - 22, id='cover',
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        body = Frame(MARGIN, BOTTOM_MARGIN, content_w, height - TOP_MARGIN - BOTTOM_MARGIN, id='body',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate('cover', [cover], onPage=self._paint_cover),
            PageTemplate('body', [body], onPage=self._paint_body),
        ])

    @property
    def content_width(self) -> float:
        return self.pagesize[0] - 2 * MARGIN

    # -- pages ---------------------------------------------------------------------------------

    def _paint_cover(self, canv, doc):
        width, height = self.pagesize
        top = height - HERO_HEIGHT
        canv.saveState()
        if self.hero:
            canv.drawImage(ImageReader(io.BytesIO(self.hero.data)), 0, top, width, HERO_HEIGHT)
        else:
            canv.setFillColor(COLOR_PRIMARY_DARK)
            canv.rect(0, top, width, HERO_HEIGHT, stroke=0, fill=1)
            canv.setFillColor(COLOR_PRIMARY)
            canv.circle(width * 0.82, top + HERO_HEIGHT * 0.78, 150, stroke=0, fill=1)
            canv.setFillColor(colors.HexColor('#14b8a6'))
            canv.circle(width * 0.95, top + 10, 90, stroke=0, fill=1)
        if self.hero:
            # A soft shade along the bottom edge of the photo.
            for i in range(10):
                canv.setFillColor(colors.black)
                canv.setFillAlpha(0.025 * (i + 1))
                canv.rect(0, top + i * 5, width, 5, stroke=0, fill=1)
            canv.setFillAlpha(1)
        canv.setFillColor(COLOR_PRIMARY)
        canv.rect(0, top - 5, width, 5, stroke=0, fill=1)
        # The label in the corner.
        label = self.kind_label.upper()
        font = bold_font_name()
        canv.setFont(font, 8.5)
        label_w = stringWidth(label, font, 8.5) + 22
        canv.setFillColor(colors.black)
        canv.setFillAlpha(0.45)
        canv.roundRect(MARGIN, height - 44, label_w, 20, 10, stroke=0, fill=1)
        canv.setFillAlpha(1)
        canv.setFillColor(colors.white)
        canv.drawString(MARGIN + 11, height - 37.5, label)
        canv.setFont(ensure_pdf_fonts()[0], 8)
        canv.setFillColor(COLOR_FAINT)
        canv.drawString(MARGIN, 30, f'Made with AdventureLog on {date.today():%b} {date.today().day}, {date.today().year}')
        canv.restoreState()

    def _paint_body(self, canv, doc):
        width, height = self.pagesize
        body, _ = ensure_pdf_fonts()
        font = bold_font_name()
        canv.saveState()
        # Header: the book's name on the left, its kind on the right, a thin rule under.
        canv.setFont(font, 8)
        canv.setFillColor(COLOR_MUTED)
        canv.drawString(MARGIN, height - 34, self._fit(self.footer_text, font, 8, width * 0.6))
        canv.setFillColor(COLOR_PRIMARY)
        canv.drawRightString(width - MARGIN, height - 34, self.kind_label.upper())
        canv.setStrokeColor(colors.HexColor('#e2e8f0'))
        canv.setLineWidth(0.6)
        canv.line(MARGIN, height - 40, width - MARGIN, height - 40)
        # Footer: page x of y.
        canv.setFont(body, 8)
        canv.setFillColor(COLOR_FAINT)
        canv.drawString(MARGIN, 30, 'Made with AdventureLog')
        pages = f'{self.page} / {self.total_pages}' if self.total_pages else str(self.page)
        canv.drawRightString(width - MARGIN, 30, pages)
        canv.restoreState()

    @staticmethod
    def _fit(text: str, font: str, size: float, max_width: float) -> str:
        if stringWidth(text, font, size) <= max_width:
            return text
        while text and stringWidth(text + '…', font, size) > max_width:
            text = text[:-1]
        return text + '…'

    # -- anchors and page numbers --------------------------------------------------------------

    def afterFlowable(self, flowable):
        if isinstance(flowable, EndMarker):
            self.last_page = self.page
            return
        key = getattr(flowable, 'anchor_key', None)
        if not key:
            return
        self.page_refs[key] = self.page
        self.canv.bookmarkPage(key)
        title = getattr(flowable, 'outline_title', None)
        if title:
            self.canv.addOutlineEntry(title, key, level=flowable.outline_level, closed=False)


def render_book(
    options: PdfOptions,
    *,
    title: str,
    kind_label: str,
    footer_text: str,
    hero: Optional[Photo],
    make_story: Callable[[Dict[str, int], int], List],
) -> bytes:
    """
    Lay the book out until its page references settle (usually twice): the first pass finds
    which page each day or place lands on, the next prints those numbers where they are listed.
    """
    refs: Dict[str, int] = {}
    total = 0
    result = b''
    for _ in range(3):
        buffer = io.BytesIO()
        doc = BookDoc(
            buffer, options, title=title, kind_label=kind_label,
            footer_text=footer_text, hero=hero, total_pages=total,
        )
        doc.build(make_story(refs, total))
        result = buffer.getvalue()
        if doc.page_refs == refs and doc.last_page == total:
            break
        refs, total = dict(doc.page_refs), doc.last_page
    return result


def cover_date_line(start: Optional[date], end: Optional[date]) -> str:
    """"Jun 12 – Jun 19, 2026"""
    if not start:
        return ''
    if not end or end == start:
        return f'{start:%b} {start.day}, {start.year}'
    if start.year == end.year:
        return f'{start:%b} {start.day} – {end:%b} {end.day}, {end.year}'
    return f'{start:%b} {start.day}, {start.year} – {end:%b} {end.day}, {end.year}'
