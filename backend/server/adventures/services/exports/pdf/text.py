"""Turning a record's text, dates and money into PDF paragraphs."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from reportlab.platypus import Paragraph
from .fonts import pdf_markup


# Letter frames are ~686pt; ItemBody leading is 13pt. Keep chunks well under that
# so a card cell (title + padding) can split across pages without LayoutError.
_MAX_PDF_PARAGRAPH_LINES = 35


_MAX_PDF_PARAGRAPH_CHARS = 2000


# Tour notes can be long; still cap so a single export cannot explode.
NOTE_PDF_MAX_LENGTH = 100_000


def plain_text(value: Optional[str], max_length: int = 2000) -> str:
    if not value:
        return ''
    text = str(value)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if max_length and len(text) > max_length:
        return text[: max_length - 3] + '...'
    return text


def _iter_text_chunks(text: str) -> List[str]:
    """Split plain text into page-friendly sections for PDF paragraphs."""
    chunks: List[str] = []
    for block in re.split(r'\n\s*\n', text):
        block = block.strip()
        if not block:
            continue
        current: List[str] = []
        current_chars = 0
        for line in block.split('\n'):
            extra = len(line) + (1 if current else 0)
            if current and (
                len(current) >= _MAX_PDF_PARAGRAPH_LINES
                or current_chars + extra > _MAX_PDF_PARAGRAPH_CHARS
            ):
                chunks.append('\n'.join(current))
                current = []
                current_chars = 0
            current.append(line)
            current_chars += extra
        if current:
            chunks.append('\n'.join(current))
    return chunks


def body_paragraphs(value: Optional[str], style, max_length: int = 2000) -> List:
    text = plain_text(value, max_length=max_length)
    if not text:
        return []
    return [Paragraph(pdf_markup(chunk), style) for chunk in _iter_text_chunks(text)]


def format_date(d: Optional[date]) -> str:
    if not d:
        return ''
    return d.strftime('%A, %B %d, %Y')


def clock_text(dt: datetime) -> str:
    return f'{dt.hour % 12 or 12}:{dt.minute:02d} {"AM" if dt.hour < 12 else "PM"}'


_UTC = ZoneInfo('UTC')


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=_UTC) if dt.tzinfo is None else dt.astimezone(_UTC)


def _is_midnight_utc(dt: datetime) -> bool:
    """Mirrors the frontend's isAllDay(): exactly 00:00:00 UTC."""
    u = _as_utc(dt)
    return (u.hour, u.minute, u.second, u.microsecond) == (0, 0, 0, 0)


def _is_end_of_day_utc(dt: datetime) -> bool:
    """Mirrors isAllDayEnd(): legacy all-day visits ended at 23:59:59 UTC."""
    u = _as_utc(dt)
    return (u.hour, u.minute, u.second) == (23, 59, 59)


def is_all_day_entry(dt: Optional[datetime], tz_name: Optional[str]) -> bool:
    """Mirrors isAllDayEntry(): lodging/transportation all-day values are midnight UTC with
    no timezone. A timed one that falls at 00:00 UTC (9 AM in Tokyo) keeps its zone (#1327)."""
    return bool(dt) and not tz_name and _is_midnight_utc(dt)


def is_visit_all_day(start: Optional[datetime], end: Optional[datetime]) -> bool:
    """Mirrors isVisitAllDay(): start at midnight UTC, end missing, at midnight or 23:59:59."""
    if not start or not _is_midnight_utc(start):
        return False
    return not end or _is_midnight_utc(end) or _is_end_of_day_utc(end)


def to_local(dt: datetime, tz_name: Optional[str]) -> datetime:
    """Stored datetimes are UTC; convert one into the entry's own timezone.
    Callers decide whether the value is all-day before calling this."""
    if not tz_name:
        return dt
    try:
        zone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return dt
    return _as_utc(dt).astimezone(zone)


def entry_local(dt: datetime, tz_name: Optional[str]) -> datetime:
    """A lodging/transportation value as shown: all-day stays as stored, timed is converted."""
    return dt if is_all_day_entry(dt, tz_name) else to_local(dt, tz_name)


def visit_dates(start: Optional[datetime], end: Optional[datetime], tz_name: Optional[str]) -> Tuple[Optional[date], Optional[date]]:
    """Calendar dates of a visit. Both ends are converted, or (all-day) neither is."""
    if is_visit_all_day(start, end):
        return (_as_utc(start).date() if start else None, _as_utc(end).date() if end else None)
    return (
        to_local(start, tz_name).date() if start else None,
        to_local(end, tz_name).date() if end else None,
    )


def format_datetime(dt: Optional[datetime], tz_name: Optional[str] = None) -> str:
    """"Jun 5, 2026" for an all-day entry, else "Jun 5, 2026 3:00 PM (Europe/Paris)" in that zone."""
    if not dt:
        return ''
    if is_all_day_entry(dt, tz_name):
        return f'{dt:%b} {dt.day}, {dt.year}'
    local = to_local(dt, tz_name)
    day = f'{local:%b} {local.day}, {local.year}'
    suffix = f' ({tz_name})' if tz_name else ''
    return f'{day} {clock_text(local)}{suffix}'


def money_parts(value, currency=None):
    """(amount as a Decimal, currency code) of a price that may be a Money value or a plain number."""
    if value is None:
        return None, str(currency or 'USD')
    if hasattr(value, 'amount'):
        return Decimal(value.amount), str(getattr(value, 'currency', None) or currency or 'USD')
    return Decimal(str(value)), str(currency or 'USD')


def format_money(amount, currency: Optional[str] = None) -> str:
    """"1,234.50 EUR". Takes a Money value or a number with its currency."""
    try:
        number, code = money_parts(amount, currency)
    except Exception:
        return f'{amount} {currency or "USD"}'
    if number is None:
        return ''
    return f'{number:,.2f} {code}'
