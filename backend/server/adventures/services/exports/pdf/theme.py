"""Colours and text styles of the printed book (readable on white paper)."""

from __future__ import annotations

from typing import Dict

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle

from .fonts import bold_font_name, ensure_pdf_fonts

COLOR_PRIMARY = colors.HexColor('#0d9488')
COLOR_PRIMARY_DARK = colors.HexColor('#0f766e')
COLOR_PRIMARY_TINT = colors.HexColor('#ccfbf1')
COLOR_INK = colors.HexColor('#0f172a')
COLOR_BODY = colors.HexColor('#334155')
COLOR_MUTED = colors.HexColor('#64748b')
COLOR_FAINT = colors.HexColor('#94a3b8')
COLOR_BORDER = colors.HexColor('#e2e8f0')
COLOR_RULE = colors.HexColor('#cbd5e1')
COLOR_LIGHT_BG = colors.HexColor('#f8fafc')
COLOR_WHITE = colors.white

# One colour per day on the maps and the day tabs; they repeat after eight days.
DAY_COLORS = [
    '#0d9488', '#2563eb', '#db2777', '#d97706',
    '#7c3aed', '#059669', '#dc2626', '#0891b2',
]

# Marker colour of each kind of entry on the timeline.
TYPE_COLORS = {
    'location': '#0d9488',
    'transportation': '#2563eb',
    'lodging': '#7c3aed',
    'note': '#d97706',
    'checklist': '#059669',
}

TYPE_LABELS = {
    'location': 'Place',
    'transportation': 'Transport',
    'lodging': 'Stay',
    'note': 'Note',
    'checklist': 'Checklist',
}

# Category colours in the field guide; they repeat after twelve categories.
CATEGORY_COLORS = [
    '#0d9488', '#2563eb', '#db2777', '#d97706', '#7c3aed', '#059669',
    '#dc2626', '#0891b2', '#65a30d', '#c026d3', '#ea580c', '#4f46e5',
]


def day_color(index: int) -> str:
    """The colour for the day at ``index`` (zero-based)."""
    return DAY_COLORS[index % len(DAY_COLORS)]


def hex_color(value: str) -> colors.Color:
    return colors.HexColor(value)


def build_styles() -> Dict[str, ParagraphStyle]:
    body, _ = ensure_pdf_fonts()
    bold = bold_font_name()

    def style(name: str, **kw) -> ParagraphStyle:
        kw.setdefault('fontName', body)
        kw.setdefault('textColor', COLOR_BODY)
        return ParagraphStyle(name, **kw)

    return {
        'CoverTitle': style('CoverTitle', fontName=bold, fontSize=34, leading=38, textColor=COLOR_INK),
        'CoverKicker': style('CoverKicker', fontName=bold, fontSize=9, leading=12, textColor=COLOR_PRIMARY, spaceAfter=6),
        'CoverDates': style('CoverDates', fontSize=14, leading=19, textColor=COLOR_BODY, spaceAfter=4),
        'CoverBody': style('CoverBody', fontSize=10.5, leading=15, textColor=COLOR_BODY),
        'PageTitle': style('PageTitle', fontName=bold, fontSize=20, leading=24, textColor=COLOR_INK, spaceAfter=4),
        'SectionHeading': style('SectionHeading', fontName=bold, fontSize=13, leading=17, textColor=COLOR_PRIMARY_DARK, spaceBefore=12, spaceAfter=6),
        'GroupHeading': style('GroupHeading', fontName=bold, fontSize=15, leading=19, textColor=COLOR_INK),
        'Kicker': style('Kicker', fontName=bold, fontSize=8, leading=10, textColor=COLOR_MUTED),
        'DayKicker': style('DayKicker', fontName=bold, fontSize=9, leading=11, textColor=COLOR_WHITE),
        'DayTitle': style('DayTitle', fontName=bold, fontSize=18, leading=22, textColor=COLOR_WHITE),
        'DayDesc': style('DayDesc', fontSize=9.5, leading=13, textColor=COLOR_WHITE),
        'ItemTitle': style('ItemTitle', fontName=bold, fontSize=11.5, leading=14.5, textColor=COLOR_INK, spaceAfter=1),
        'ItemMeta': style('ItemMeta', fontSize=8.5, leading=11.5, textColor=COLOR_MUTED, spaceAfter=1),
        'ItemBody': style('ItemBody', fontSize=9.5, leading=13, textColor=COLOR_BODY, spaceAfter=3),
        'Time': style('Time', fontName=bold, fontSize=9, leading=11, textColor=COLOR_INK, alignment=TA_RIGHT),
        'TimeSub': style('TimeSub', fontSize=7.5, leading=9.5, textColor=COLOR_MUTED, alignment=TA_RIGHT),
        'Code': style('Code', fontName=bold, fontSize=22, leading=24, textColor=COLOR_INK),
        'CodeRight': style('CodeRight', fontName=bold, fontSize=22, leading=24, textColor=COLOR_INK, alignment=TA_RIGHT),
        'CodeSub': style('CodeSub', fontSize=8, leading=10, textColor=COLOR_MUTED),
        'CodeSubRight': style('CodeSubRight', fontSize=8, leading=10, textColor=COLOR_MUTED, alignment=TA_RIGHT),
        'CodeArrow': style('CodeArrow', fontSize=14, leading=24, textColor=COLOR_FAINT, alignment=TA_CENTER),
        'Stat': style('Stat', fontName=bold, fontSize=20, leading=22, textColor=COLOR_INK, alignment=TA_CENTER),
        'StatLabel': style('StatLabel', fontName=bold, fontSize=7, leading=9, textColor=COLOR_MUTED, alignment=TA_CENTER),
        'TableHead': style('TableHead', fontName=bold, fontSize=7.5, leading=10, textColor=COLOR_MUTED),
        'TableCell': style('TableCell', fontSize=9, leading=12, textColor=COLOR_BODY),
        'TableCellBold': style('TableCellBold', fontName=bold, fontSize=9, leading=12, textColor=COLOR_INK),
        'TableCellRight': style('TableCellRight', fontSize=9, leading=12, textColor=COLOR_BODY, alignment=TA_RIGHT),
        'Chip': style('Chip', fontName=bold, fontSize=8, leading=10, textColor=COLOR_PRIMARY_DARK),
        'Hint': style('Hint', fontSize=8.5, leading=12, textColor=COLOR_MUTED),
        'WriteLabel': style('WriteLabel', fontName=bold, fontSize=8, leading=10, textColor=COLOR_MUTED),
        'Footer': style('Footer', fontSize=7.5, leading=9, textColor=COLOR_FAINT, alignment=TA_CENTER),
    }
