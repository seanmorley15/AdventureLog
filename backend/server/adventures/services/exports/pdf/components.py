"""The blocks both books are made of: place, transport, stay, note and checklist entries."""

from __future__ import annotations

import io
from datetime import time
from typing import Any, List, Optional, Sequence, Tuple

from reportlab.platypus import Image, KeepTogether, Paragraph, Spacer, Table, TableStyle

from core.formatting import format_short_date

from .fonts import escape_xml, pdf_markup, renderable_icon
from .layout import Ctx
from .maps import MapLeg, MapPoint
from .text import NOTE_PDF_MAX_LENGTH, body_paragraphs, format_datetime, format_money
from .theme import (
    COLOR_BORDER,
    COLOR_LIGHT_BG,
    COLOR_PRIMARY_DARK,
    TYPE_COLORS,
    TYPE_LABELS,
    hex_color,
)
from .writein import Arrow, Checkbox, Marker, QRCode, map_link

# Minimum leftover height (points) required to split an entry mid-row.
SPLIT_IN_ROW = 40
TIME_COL = 56
MARKER_COL = 30
PLACE_DESCRIPTION_MAX = 1200


def P(text: str, style) -> Paragraph:
    """A paragraph of plain text (escaped, emoji in the emoji font)."""
    return Paragraph(pdf_markup(text), style)


def link(url: str, label: str) -> str:
    return f'<link href="{escape_xml(url)}" color="#0f766e">{pdf_markup(label)}</link>'


def clock(value: Optional[time]) -> str:
    if not value:
        return ''
    return f'{value.hour % 12 or 12}:{value.minute:02d} {"AM" if value.hour < 12 else "PM"}'


def point_latlon(point) -> Optional[Tuple[float, float]]:
    """(lat, lon) of a stored point, or None when it is empty or at 0,0 (an unset marker)."""
    if point is None:
        return None
    try:
        lat, lon = float(point.y), float(point.x)
    except (AttributeError, TypeError, ValueError):
        return None
    if lat == 0 and lon == 0:
        return None
    return lat, lon


def coords_text(point) -> str:
    latlon = point_latlon(point)
    return f'{latlon[0]:.5f}, {latlon[1]:.5f}' if latlon else ''


def category_text(location) -> str:
    if not location.category:
        return ''
    icon = renderable_icon(location.category.icon or '')
    label = location.category.display_name or location.category.name or ''
    return f'{icon} {label}'.strip()


def geo_text(location) -> str:
    bits = [place.name for place in (location.city, location.region, location.country) if place]
    return ', '.join(bits)


# --- the text of each kind of entry ---------------------------------------------------------


def _extras(ctx: Ctx, rating, price_text: str, url: Optional[str]) -> Optional[Paragraph]:
    parts = []
    if rating is not None:
        parts.append(f'Rating {rating:g}/5')
    if price_text:
        parts.append(pdf_markup(price_text))
    if url:
        parts.append(link(url, 'Link'))
    if not parts:
        return None
    return Paragraph(' · '.join(p if '<' in p else pdf_markup(p) for p in parts), ctx.styles['ItemMeta'])


def place_text(ctx: Ctx, location, *, description_max: int = PLACE_DESCRIPTION_MAX, category: bool = True, visits: Optional[bool] = None) -> List:
    s = ctx.styles
    out: List = [P(location.name or 'Place', s['ItemTitle'])]
    if category and category_text(location):
        out.append(P(category_text(location), s['ItemMeta']))
    if location.location:
        out.append(P(location.location, s['ItemMeta']))
    geo = geo_text(location)
    if geo:
        out.append(P(geo, s['ItemMeta']))
    coords = coords_text(location.coordinates)
    if coords:
        out.append(P(coords, s['ItemMeta']))
    if ctx.show_visits if visits is None else visits:
        for visit in sorted(location.visits.all(), key=lambda v: v.start_date or v.created_at):
            start = visit.start_date.date() if visit.start_date else None
            end = visit.end_date.date() if visit.end_date else None
            if start and end and end != start:
                out.append(P(f'Visited {format_short_date(start)} – {format_short_date(end)}', s['ItemMeta']))
            elif start:
                out.append(P(f'Visited {format_short_date(start)}', s['ItemMeta']))
    out.extend(body_paragraphs(location.description, s['ItemBody'], max_length=description_max))
    price = format_money(location.price)
    extras = _extras(ctx, location.rating, price, location.link)
    if extras:
        out.append(extras)
    if location.tags:
        out.append(P('  '.join(f'#{tag}' for tag in location.tags), s['ItemMeta']))
    for trail in location.trails.all():
        out.append(Paragraph('Trail: ' + (link(trail.link, trail.name) if trail.link else pdf_markup(trail.name)), s['ItemMeta']))
    return out


def transport_text(ctx: Ctx, transport) -> List:
    s = ctx.styles
    out: List = []
    start = transport.start_code or ''
    end = transport.end_code or ''
    kind = (transport.type or 'other').replace('_', ' ').title()
    title = transport.name or kind
    out.append(P(title, s['ItemTitle']))
    sub = kind + (f' · {transport.flight_number}' if transport.flight_number else '')
    out.append(P(sub, s['ItemMeta']))
    origin, destination = transport.from_location or '', transport.to_location or ''
    if start or end:
        # Big codes with the place names under them: the way a boarding pass reads.
        row = [[
            [P(start or origin or '—', s['Code']), P(origin if start else '', s['CodeSub'])],
            Arrow(36, 24),
            [P(end or destination or '—', s['CodeRight']), P(destination if end else '', s['CodeSubRight'])],
        ]]
        route = Table(row, colWidths=[None, 40, None], hAlign='LEFT')
        route.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        out.append(route)
    elif origin or destination:
        out.append(P(f'{origin or "—"} to {destination or "—"}', s['ItemBody']))
    if transport.date:
        out.append(P('Departs ' + format_datetime(transport.date, transport.start_timezone), s['ItemMeta']))
    if transport.end_date:
        out.append(P('Arrives ' + format_datetime(transport.end_date, transport.end_timezone), s['ItemMeta']))
    out.extend(body_paragraphs(transport.description, s['ItemBody']))
    price = format_money(transport.price, transport.price_currency)
    extras = _extras(ctx, transport.rating, price, transport.link)
    if extras:
        out.append(extras)
    return out


def lodging_text(ctx: Ctx, lodging) -> List:
    s = ctx.styles
    out: List = [P(lodging.name or 'Stay', s['ItemTitle'])]
    kind = (lodging.type or '').replace('_', ' ').title()
    if kind:
        out.append(P(kind, s['ItemMeta']))
    if lodging.location:
        out.append(P(lodging.location, s['ItemMeta']))
    coords = coords_text(lodging.coordinates)
    if coords:
        out.append(P(coords, s['ItemMeta']))
    if lodging.check_in or lodging.check_out:
        check_in = format_datetime(lodging.check_in, lodging.timezone) if lodging.check_in else '—'
        check_out = format_datetime(lodging.check_out, lodging.timezone) if lodging.check_out else '—'
        nights = ''
        if lodging.check_in and lodging.check_out:
            count = (lodging.check_out.date() - lodging.check_in.date()).days
            if count > 0:
                nights = f' · {count} night{"s" if count != 1 else ""}'
        out.append(P(f'Check-in {check_in}', s['ItemMeta']))
        out.append(P(f'Check-out {check_out}{nights}', s['ItemMeta']))
    if lodging.reservation_number:
        out.append(Paragraph(f'<b>Confirmation {pdf_markup(lodging.reservation_number)}</b>', s['ItemMeta']))
    out.extend(body_paragraphs(lodging.description, s['ItemBody'], max_length=PLACE_DESCRIPTION_MAX))
    price = format_money(lodging.price, lodging.price_currency)
    extras = _extras(ctx, lodging.rating, price, lodging.link)
    if extras:
        out.append(extras)
    return out


def note_text(ctx: Ctx, note) -> List:
    s = ctx.styles
    out: List = [P(note.name or 'Note', s['ItemTitle'])]
    if note.date:
        out.append(P(format_short_date(note.date), s['ItemMeta']))
    out.extend(body_paragraphs(note.content, s['ItemBody'], max_length=NOTE_PDF_MAX_LENGTH))
    for url in note.links or []:
        if url:
            out.append(Paragraph(link(url, url), s['ItemMeta']))
    return out


def checklist_text(ctx: Ctx, checklist) -> List:
    s = ctx.styles
    out: List = [P(checklist.name or 'Checklist', s['ItemTitle'])]
    if checklist.date:
        out.append(P(format_short_date(checklist.date), s['ItemMeta']))
    for item in checklist.checklistitem_set.all():
        # One table per item, so a long checklist can run over a page.
        row = Table([[Checkbox(10, item.is_checked), P(item.name or '', s['ItemBody'])]], colWidths=[18, None])
        row.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ]))
        out.append(row)
    return out


_TEXT = {
    'location': place_text,
    'transportation': transport_text,
    'lodging': lodging_text,
    'note': note_text,
    'checklist': checklist_text,
}


def side_column(ctx: Ctx, model: str, obj: Any, width: float = 104) -> List:
    """A photo and a QR code for the right-hand side of a place or stay."""
    side: List = []
    if model in ('location', 'lodging'):
        photo = ctx.media.thumbnail(obj)
        if photo:
            side.append(photo.flowable(width, max_height=90))
        latlon = point_latlon(obj.coordinates)
        if latlon:
            if side:
                side.append(Spacer(1, 6))
            side.append(QRCode(map_link(*latlon), size=38))
    return side


def entry_content(ctx: Ctx, model: str, obj: Any, inner_width: float) -> List:
    """
    The flowables of one entry, one per row. A place or stay with a photo or QR code is one
    two-column row (text left, photo right); everything else is a flowable per line so long
    notes and checklists can continue on the next page.
    """
    text = _TEXT[model](ctx, obj)
    side = side_column(ctx, model, obj)
    if not side:
        return text
    side_w = 104
    block = Table([[text, side]], colWidths=[inner_width - side_w - 12, side_w])
    block.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (0, 0), 12), ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return [block]


def entry_table(
    ctx: Ctx,
    model: str,
    obj: Any,
    *,
    number: Optional[int] = None,
    time_text: str = '',
    time_sub: str = '',
    optional: bool = False,
) -> List:
    """One entry of a day or a list: time on the left, a numbered marker, then the card."""
    s = ctx.styles
    color = TYPE_COLORS.get(model, '#64748b')
    label = TYPE_LABELS.get(model, model.title()).upper()
    kicker = f'<font color="{color}">{label}</font>' + ('  ·  OPTIONAL' if optional else '')
    # With no number or time the card runs the full width of the page.
    gutter = number is not None or bool(time_text)
    time_w, marker_w = (TIME_COL, MARKER_COL) if gutter else (0.01, 0.01)
    inner = ctx.width - time_w - marker_w - 24
    content = entry_content(ctx, model, obj, inner)
    # The label and the first lines of the entry stay together, so a card never starts with only its label at the foot of a page.
    rows = [[Paragraph(kicker, s['Kicker']), *content[:2]], *content[2:]]

    table_rows = []
    for index, flowable in enumerate(rows):
        if index == 0:
            time_cell: Any = ''
            if time_text:
                time_cell = [Paragraph(pdf_markup(time_text), s['Time'])]
                if time_sub:
                    time_cell.append(Paragraph(pdf_markup(time_sub), s['TimeSub']))
            marker = Marker(str(number), color, 20) if number is not None else ''
            table_rows.append([time_cell, marker, flowable])
        else:
            table_rows.append(['', '', flowable])

    table = Table(table_rows, colWidths=[time_w, marker_w, ctx.width - time_w - marker_w],
                  splitByRow=1, splitInRow=SPLIT_IN_ROW)
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (2, 0), (2, -1), COLOR_LIGHT_BG),
        ('LINEBEFORE', (2, 0), (2, -1), 2.2, hex_color(color)),
        ('LINEABOVE', (2, 0), (2, 0), 0.5, COLOR_BORDER),
        ('LINEBELOW', (2, -1), (2, -1), 0.5, COLOR_BORDER),
        ('LINEAFTER', (2, 0), (2, -1), 0.5, COLOR_BORDER),
        ('LEFTPADDING', (0, 0), (1, -1), 0), ('RIGHTPADDING', (0, 0), (0, -1), 8 if gutter else 0),
        ('LEFTPADDING', (2, 0), (2, -1), 12), ('RIGHTPADDING', (2, 0), (2, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, 0), 9), ('BOTTOMPADDING', (0, -1), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    if model in ('note', 'checklist'):
        # These can be long, so they may continue on the next page.
        return [table, Spacer(1, 9)]
    # A place, stay or journey is short: keep it whole rather than leave its label at the foot of a page.
    return [KeepTogether([table, Spacer(1, 9)])]


# --- time of an entry on the timeline ---------------------------------------------------------


def entry_time(model: str, obj: Any, item=None) -> Tuple[str, str]:
    """The time shown to the left of an entry, and a word under it."""
    start = clock(getattr(item, 'start_time', None)) if item else ''
    end = clock(getattr(item, 'end_time', None)) if item else ''
    if model == 'transportation':
        if not start and obj.date and (obj.date.hour or obj.date.minute):
            start = clock(obj.date.time())
        if not end and obj.end_date and (obj.end_date.hour or obj.end_date.minute):
            end = clock(obj.end_date.time())
        return start, (f'arrives {end}' if end else '')
    if model == 'lodging':
        if not start and obj.check_in and (obj.check_in.hour or obj.check_in.minute):
            start = clock(obj.check_in.time())
        return start, 'check-in' if start else ''
    return start, (f'until {end}' if end else '')


# --- pieces of a page ---------------------------------------------------------------------------


def section_heading(ctx: Ctx, text: str) -> List:
    return [Paragraph(pdf_markup(text), ctx.styles['SectionHeading'])]


def day_band(ctx: Ctx, number: int, color: str, kicker: str, title: str, description: Optional[str], overnight: Sequence) -> Table:
    """The coloured header at the top of a day."""
    s = ctx.styles
    rows = [[Paragraph(pdf_markup(kicker), s['DayKicker'])], [Paragraph(pdf_markup(title), s['DayTitle'])]]
    if description:
        rows.append([Paragraph(pdf_markup(description), s['DayDesc'])])
    if overnight:
        names = ', '.join(pdf_markup(item.name) for item in overnight)
        rows.append([Paragraph(f'<b>Staying at</b> {names}', s['DayDesc'])])
    band = Table(rows, colWidths=[ctx.width])
    band.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), hex_color(color)),
        ('LEFTPADDING', (0, 0), (-1, -1), 16), ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, 0), 14), ('BOTTOMPADDING', (0, -1), (-1, -1), 14),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    return band


def stat_strip(ctx: Ctx, stats: Sequence[Tuple[str, str]]) -> Optional[Table]:
    """A row of big numbers with a small label under each."""
    stats = [(value, label) for value, label in stats if value]
    if not stats:
        return None
    s = ctx.styles
    cell_w = ctx.width / len(stats)
    table = Table(
        [[Paragraph(pdf_markup(v), s['Stat']) for v, _ in stats], [Paragraph(pdf_markup(l.upper()), s['StatLabel']) for _, l in stats]],
        colWidths=[cell_w] * len(stats),
    )
    commands = [
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, 0), 10), ('BOTTOMPADDING', (0, 0), (-1, 0), 1),
        ('TOPPADDING', (0, 1), (-1, 1), 0), ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]
    for col in range(1, len(stats)):
        commands.append(('LINEBEFORE', (col, 0), (col, -1), 0.5, COLOR_BORDER))
    table.setStyle(TableStyle(commands))
    return table


def map_flowable(ctx: Ctx, points: Sequence[MapPoint], height: float, legs: Sequence[MapLeg] = ()) -> Optional[Image]:
    """A map of ``points`` as wide as the page, or None when there is nothing to show."""
    data = ctx.maps.render(points, ctx.width, height, legs)
    if not data:
        return None
    return Image(io.BytesIO(data), width=ctx.width, height=height)


def legend(ctx: Ctx, entries: Sequence[Tuple[str, str, str]], per_row: int = 4) -> Optional[Table]:
    """Coloured markers with a label each: (marker text, colour, label)."""
    if not entries:
        return None
    cells: List[Any] = []
    for marker, color, label in entries:
        cell = Table([[Marker(marker, color, 14), Paragraph(pdf_markup(label), ctx.styles['ItemMeta'])]], colWidths=[20, None])
        cell.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        cells.append(cell)
    rows = [cells[i:i + per_row] for i in range(0, len(cells), per_row)]
    for row in rows:
        row.extend([''] * (per_row - len(row)))
    table = Table(rows, colWidths=[ctx.width / per_row] * per_row)
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    return table


def grid_table(ctx: Ctx, head: Sequence[str], rows: Sequence[Sequence[Any]], widths: Sequence[float]) -> Table:
    """A table with a header row, thin rules between rows, and no fill."""
    s = ctx.styles
    data = [[Paragraph(pdf_markup(h.upper()), s['TableHead']) for h in head]]
    for row in rows:
        data.append([cell if not isinstance(cell, str) else Paragraph(pdf_markup(cell), s['TableCell']) for cell in row])
    total = sum(widths)
    table = Table(data, colWidths=[w / total * ctx.width for w in widths], repeatRows=1)
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, COLOR_PRIMARY_DARK),
        ('LINEBELOW', (0, 1), (-1, -1), 0.4, COLOR_BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return table
