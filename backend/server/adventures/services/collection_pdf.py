"""
Build a printable PDF itinerary from a Collection and its related content.
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Prefetch
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from adventures.models import (
    Checklist,
    ChecklistItem,
    Collection,
    CollectionItineraryDay,
    CollectionItineraryItem,
    Location,
    Lodging,
    Note,
    Transportation,
)
from adventures.services.pdf_fonts import (
    apply_fonts_to_styles,
    ensure_pdf_fonts,
    escape_xml,
    pdf_markup,
)

# Brand-adjacent palette (readable on white paper)
COLOR_PRIMARY = colors.HexColor('#0d9488')
COLOR_MUTED = colors.HexColor('#64748b')
COLOR_BORDER = colors.HexColor('#e2e8f0')
COLOR_LIGHT_BG = colors.HexColor('#f8fafc')

# Letter frames are ~686pt; ItemBody leading is 13pt. Keep chunks well under that
# so a card cell (title + padding) can split across pages without LayoutError.
_MAX_PDF_PARAGRAPH_LINES = 35
_MAX_PDF_PARAGRAPH_CHARS = 2000
# Tour notes can be long; still cap so a single export cannot explode.
_NOTE_PDF_MAX_LENGTH = 100_000
# Minimum leftover height (points) required to split a card mid-row.
_CARD_SPLIT_IN_ROW = 40


def get_collection_for_pdf(collection_id) -> Collection:
    """Load a collection with relations needed for PDF export."""
    return (
        Collection.objects.filter(pk=collection_id)
        .select_related('primary_image', 'user')
        .prefetch_related(
            Prefetch(
                'locations',
                queryset=Location.objects.select_related(
                    'category', 'country', 'region', 'city'
                ).prefetch_related('visits'),
            ),
            'transportation_set',
            'note_set',
            Prefetch(
                'lodging_set',
                queryset=Lodging.objects.all(),
            ),
            Prefetch(
                'checklist_set',
                queryset=Checklist.objects.prefetch_related(
                    Prefetch('checklistitem_set', queryset=ChecklistItem.objects.order_by('name'))
                ),
            ),
            Prefetch(
                'itinerary_items',
                queryset=CollectionItineraryItem.objects.select_related('content_type').order_by(
                    'date', 'order'
                ),
            ),
            'itinerary_days',
        )
        .get()
    )


def _plain_text(value: Optional[str], max_length: int = 2000) -> str:
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


def _body_paragraphs(value: Optional[str], style, max_length: int = 2000) -> List:
    text = _plain_text(value, max_length=max_length)
    if not text:
        return []
    return [Paragraph(pdf_markup(chunk), style) for chunk in _iter_text_chunks(text)]


def _format_date(d: Optional[date]) -> str:
    if not d:
        return ''
    return d.strftime('%A, %B %d, %Y')


def _format_short_date(d: Optional[date]) -> str:
    if not d:
        return ''
    return d.strftime('%b %d, %Y')


def _format_datetime(dt: Optional[datetime], tz_name: Optional[str] = None) -> str:
    if not dt:
        return ''
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        return dt.strftime('%b %d, %Y')
    suffix = f' ({tz_name})' if tz_name else ''
    return dt.strftime('%b %d, %Y %I:%M %p').lstrip('0') + suffix


def _format_money(amount, currency: Optional[str]) -> str:
    if amount is None:
        return ''
    cur = currency or 'USD'
    try:
        return f'{amount} {cur}'
    except Exception:
        return str(amount)


def _trip_day_count(start: Optional[date], end: Optional[date]) -> Optional[int]:
    if not start or not end:
        return None
    return (end - start).days + 1


def _build_lookups(collection: Collection) -> Dict[str, Dict[str, Any]]:
    return {
        'location': {str(loc.id): loc for loc in collection.locations.all()},
        'transportation': {str(t.id): t for t in collection.transportation_set.all()},
        'lodging': {str(l.id): l for l in collection.lodging_set.all()},
        'note': {str(n.id): n for n in collection.note_set.all()},
        'checklist': {str(c.id): c for c in collection.checklist_set.all()},
    }


def _resolve_item(
    itinerary_item: CollectionItineraryItem, lookups: Dict[str, Dict[str, Any]]
) -> Tuple[Optional[str], Optional[Any]]:
    model = itinerary_item.content_type.model
    obj = lookups.get(model, {}).get(str(itinerary_item.object_id))
    return model, obj


def _overnight_lodging_for_date(collection: Collection, day: date, scheduled_lodging_ids: set) -> List[Lodging]:
    result = []
    target = day
    for lodging in collection.lodging_set.all():
        if str(lodging.id) not in scheduled_lodging_ids:
            continue
        if not lodging.check_in or not lodging.check_out:
            continue
        check_in = lodging.check_in.date()
        check_out = lodging.check_out.date()
        if check_in <= target < check_out:
            result.append(lodging)
    return result


def _iter_trip_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _scheduled_keys(collection: Collection) -> set:
    keys = set()
    for item in collection.itinerary_items.all():
        keys.add((item.content_type.model, str(item.object_id)))
    return keys


def _group_itinerary_days(collection: Collection) -> Tuple[List[Dict[str, Any]], List[CollectionItineraryItem], Dict[str, Dict[str, Any]]]:
    """Mirror the web planner: one section per calendar day in the trip range."""
    lookups = _build_lookups(collection)
    day_meta = {d.date: d for d in collection.itinerary_days.all()}

    dated_items: Dict[date, List[CollectionItineraryItem]] = {}
    global_items: List[CollectionItineraryItem] = []
    scheduled_lodging_ids = set()

    for item in collection.itinerary_items.all():
        model = item.content_type.model
        if model == 'lodging':
            scheduled_lodging_ids.add(str(item.object_id))
        if item.is_global:
            global_items.append(item)
        elif item.date:
            dated_items.setdefault(item.date, []).append(item)

    for items in dated_items.values():
        items.sort(key=lambda x: x.order)

    start = collection.start_date
    end = collection.end_date
    if not start or not end:
        if dated_items:
            dates = sorted(dated_items.keys())
            start = dates[0]
            end = dates[-1]
        else:
            return []

    days: List[Dict[str, Any]] = []
    for day in _iter_trip_dates(start, end):
        resolved = []
        for it in dated_items.get(day, []):
            model, obj = _resolve_item(it, lookups)
            if obj is not None:
                resolved.append({'order': it.order, 'type': model, 'object': obj})

        overnight = _overnight_lodging_for_date(collection, day, scheduled_lodging_ids)
        meta = day_meta.get(day)
        days.append(
            {
                'date': day,
                'display_date': _format_date(day),
                'day_name': meta.name if meta and meta.name else None,
                'day_description': _plain_text(meta.description) if meta and meta.description else None,
                'items': resolved,
                'overnight_lodging': overnight,
            }
        )
    return days, global_items, lookups


def _item_type_label(model: str) -> str:
    return {
        'location': 'Location',
        'transportation': 'Transport',
        'lodging': 'Stay',
        'note': 'Note',
        'checklist': 'Checklist',
    }.get(model, model.title())


def _location_paragraphs(location: Location, styles) -> List:
    flowables = []
    title = pdf_markup(location.name or 'Location')
    category = ''
    if location.category:
        icon = location.category.icon or ''
        label = location.category.display_name or location.category.name
        category = pdf_markup(f'{icon} {label}'.strip())
    flowables.append(Paragraph(f'<b>{title}</b>{f" <font color=\"#64748b\">{category}</font>" if category else ""}', styles['ItemTitle']))

    if location.location:
        flowables.append(Paragraph(pdf_markup(location.location), styles['ItemMeta']))

    geo_bits = []
    if location.city:
        geo_bits.append(location.city.name)
    if location.region:
        geo_bits.append(location.region.name)
    if location.country:
        geo_bits.append(location.country.name)
    if geo_bits:
        flowables.append(Paragraph(pdf_markup(', '.join(geo_bits)), styles['ItemMeta']))

    for visit in location.visits.all().order_by('start_date'):
        start = visit.start_date.date() if visit.start_date else None
        end = visit.end_date.date() if visit.end_date else None
        if start and end and end != start:
            flowables.append(
                Paragraph(
                    f'Visit: {_format_short_date(start)} – {_format_short_date(end)}',
                    styles['ItemMeta'],
                )
            )
        elif start:
            flowables.append(Paragraph(f'Visit: {_format_short_date(start)}', styles['ItemMeta']))

    flowables.extend(_body_paragraphs(location.description, styles['ItemBody']))

    extras = []
    if location.rating is not None:
        extras.append(f'Rating: {location.rating}/5')
    if location.price is not None:
        extras.append(_format_money(location.price.amount, str(location.price.currency)))
    if location.link:
        extras.append(f'<link href="{escape_xml(location.link)}">Link</link>')
    if extras:
        flowables.append(Paragraph(' · '.join(extras), styles['ItemMeta']))

    return flowables


def _transportation_paragraphs(transport: Transportation, styles) -> List:
    flowables = []
    title = pdf_markup(transport.name or transport.type or 'Transport')
    flowables.append(Paragraph(f'<b>{title}</b> <font color="#64748b">({pdf_markup(transport.type)})</font>', styles['ItemTitle']))

    route_parts = []
    if transport.from_location or transport.start_code:
        origin = transport.from_location or transport.start_code or ''
        route_parts.append(pdf_markup(origin))
    if transport.to_location or transport.end_code:
        dest = transport.to_location or transport.end_code or ''
        if route_parts:
            route_parts.append('→')
        route_parts.append(pdf_markup(dest))
    if route_parts:
        flowables.append(Paragraph(' '.join(route_parts), styles['ItemMeta']))

    if transport.date:
        line = _format_datetime(transport.date, transport.start_timezone)
        if transport.end_date:
            line += f' – {_format_datetime(transport.end_date, transport.end_timezone)}'
        flowables.append(Paragraph(line, styles['ItemMeta']))

    if transport.flight_number:
        flowables.append(Paragraph(f'Flight: {pdf_markup(transport.flight_number)}', styles['ItemMeta']))

    flowables.extend(_body_paragraphs(transport.description, styles['ItemBody']))

    extras = []
    if transport.rating is not None:
        extras.append(f'Rating: {transport.rating}/5')
    if transport.price is not None:
        extras.append(_format_money(transport.price, transport.price_currency))
    if transport.link:
        extras.append(f'<link href="{escape_xml(transport.link)}">Link</link>')
    if extras:
        flowables.append(Paragraph(' · '.join(extras), styles['ItemMeta']))

    return flowables


def _lodging_paragraphs(lodging: Lodging, styles) -> List:
    flowables = []
    title = pdf_markup(lodging.name or 'Stay')
    flowables.append(
        Paragraph(
            f'<b>{title}</b> <font color="#64748b">({pdf_markup(lodging.type)})</font>',
            styles['ItemTitle'],
        )
    )
    if lodging.location:
        flowables.append(Paragraph(pdf_markup(lodging.location), styles['ItemMeta']))
    if lodging.check_in or lodging.check_out:
        check_in = _format_datetime(lodging.check_in, lodging.timezone) if lodging.check_in else '—'
        check_out = _format_datetime(lodging.check_out, lodging.timezone) if lodging.check_out else '—'
        flowables.append(Paragraph(f'Check-in: {check_in} · Check-out: {check_out}', styles['ItemMeta']))
    if lodging.reservation_number:
        flowables.append(Paragraph(f'Confirmation: {pdf_markup(lodging.reservation_number)}', styles['ItemMeta']))

    flowables.extend(_body_paragraphs(lodging.description, styles['ItemBody']))

    extras = []
    if lodging.rating is not None:
        extras.append(f'Rating: {lodging.rating}/5')
    if lodging.price is not None:
        extras.append(_format_money(lodging.price, lodging.price_currency))
    if lodging.link:
        extras.append(f'<link href="{escape_xml(lodging.link)}">Link</link>')
    if extras:
        flowables.append(Paragraph(' · '.join(extras), styles['ItemMeta']))

    return flowables


def _note_paragraphs(note: Note, styles) -> List:
    flowables = []
    flowables.append(Paragraph(f'<b>{pdf_markup(note.name or "Note")}</b>', styles['ItemTitle']))
    if note.date:
        flowables.append(Paragraph(_format_short_date(note.date), styles['ItemMeta']))
    flowables.extend(
        _body_paragraphs(note.content, styles['ItemBody'], max_length=_NOTE_PDF_MAX_LENGTH)
    )
    if note.links:
        for link in note.links:
            if link:
                flowables.append(
                    Paragraph(
                        f'<link href="{escape_xml(link)}">{pdf_markup(link)}</link>',
                        styles['ItemMeta'],
                    )
                )
    return flowables


def _checklist_paragraphs(checklist: Checklist, styles, _body_font: str, _emoji_font: str | None) -> List:
    flowables = []
    flowables.append(Paragraph(f'<b>{pdf_markup(checklist.name or "Checklist")}</b>', styles['ItemTitle']))
    if checklist.date:
        flowables.append(Paragraph(_format_short_date(checklist.date), styles['ItemMeta']))
    mark_style = ParagraphStyle(
        'ChecklistMark',
        parent=styles['ItemMeta'],
        fontSize=10,
        textColor=COLOR_MUTED,
    )
    rows = []
    for item in checklist.checklistitem_set.all():
        mark = '☑' if item.is_checked else '☐'
        rows.append([
            Paragraph(pdf_markup(mark), mark_style),
            Paragraph(pdf_markup(item.name or ''), styles['ItemBody']),
        ])
    if rows:
        # One row per item (not a nested unsplittable table) so long checklists paginate.
        for row in rows:
            item_table = Table([row], colWidths=[0.35 * inch, 6.0 * inch])
            item_table.setStyle(
                TableStyle(
                    [
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ]
                )
            )
            flowables.append(item_table)
    return flowables


def _item_flowables(
    model: str, obj: Any, styles, body_font: str, emoji_font: str | None
) -> List:
    if obj is None:
        return []
    if model == 'location':
        return _location_paragraphs(obj, styles)
    if model == 'transportation':
        return _transportation_paragraphs(obj, styles)
    if model == 'lodging':
        return _lodging_paragraphs(obj, styles)
    if model == 'note':
        return _note_paragraphs(obj, styles)
    if model == 'checklist':
        return _checklist_paragraphs(obj, styles, body_font, emoji_font)
    return []


def _item_card(
    model: str, obj: Any, order: int, styles, body_font: str, emoji_font: str | None
) -> List:
    """Render a single itinerary entry inside a shaded card."""
    inner = [
        Paragraph(
            f'<font color="#0d9488"><b>{order}.</b></font> '
            f'<font color="#64748b">{_item_type_label(model).upper()}</font>',
            styles['ItemLabel'],
        ),
    ]
    inner.extend(_item_flowables(model, obj, styles, body_font, emoji_font))
    # One flowable per row so ReportLab can page-split between sections. Do not
    # repeatRows: that reprints "1. NOTE" at every page/row split. splitInRow
    # still splits an oversized cell (e.g. a still-too-tall paragraph) mid-row.
    rows = [[flowable] for flowable in inner]
    card = Table(
        rows,
        colWidths=[6.5 * inch],
        splitByRow=1,
        splitInRow=_CARD_SPLIT_IN_ROW,
    )
    card.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
                ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (0, 0), 10),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
            ]
        )
    )
    return [card, Spacer(1, 10)]


def _cover_image_flowable(collection: Collection, max_width: float = 6.5 * inch) -> Optional[Image]:
    image_field = None
    if collection.primary_image and collection.primary_image.image:
        image_field = collection.primary_image.image
    if not image_field:
        return None
    try:
        with image_field.open('rb') as fh:
            pil = PILImage.open(fh)
            pil = pil.convert('RGB')
            buf = io.BytesIO()
            pil.save(buf, format='JPEG', quality=85)
            buf.seek(0)
        img = Image(buf)
        ratio = img.imageHeight / float(img.imageWidth)
        img.drawWidth = max_width
        img.drawHeight = max_width * ratio
        if img.drawHeight > 3.5 * inch:
            img.drawHeight = 3.5 * inch
            img.drawWidth = img.drawHeight / ratio
        return img
    except Exception:
        return None


def _section_heading(text: str, styles) -> List:
    return [
        Paragraph(text, styles['SectionHeading']),
        Spacer(1, 8),
    ]


def _folder_sections(
    collection: Collection,
    styles,
    body_font: str,
    emoji_font: str | None,
    *,
    only_unscheduled: bool = False,
    scheduled_keys: Optional[set] = None,
) -> List:
    """List linked content by type (optionally excluding itinerary-scheduled items)."""
    story = []
    scheduled_keys = scheduled_keys or set()

    def include(model: str, obj_id: str) -> bool:
        if not only_unscheduled:
            return True
        return (model, str(obj_id)) not in scheduled_keys

    sections = [
        ('Locations', 'location', collection.locations.all()),
        ('Transport', 'transportation', collection.transportation_set.all()),
        ('Stays', 'lodging', collection.lodging_set.all()),
        ('Notes', 'note', collection.note_set.all()),
        ('Checklists', 'checklist', collection.checklist_set.all()),
    ]

    order = 1
    for heading, model, queryset in sections:
        items = [obj for obj in queryset if include(model, obj.id)]
        if not items:
            continue
        story.extend(_section_heading(heading, styles))
        for obj in items:
            story.extend(_item_card(model, obj, order, styles, body_font, emoji_font))
            order += 1
    return story


def build_collection_pdf(collection: Collection) -> bytes:
    """Return PDF bytes for the given collection."""
    body_font, emoji_font = ensure_pdf_fonts()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=collection.name or 'Trip',
        author='AdventureLog',
    )

    base = getSampleStyleSheet()
    styles = {
        'CoverTitle': ParagraphStyle(
            'CoverTitle',
            parent=base['Title'],
            fontSize=26,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=12,
        ),
        'CoverSubtitle': ParagraphStyle(
            'CoverSubtitle',
            parent=base['Normal'],
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=COLOR_MUTED,
            spaceAfter=6,
        ),
        'SectionHeading': ParagraphStyle(
            'SectionHeading',
            parent=base['Heading2'],
            fontSize=14,
            leading=18,
            textColor=COLOR_PRIMARY,
            spaceBefore=8,
            spaceAfter=4,
        ),
        'DayHeading': ParagraphStyle(
            'DayHeading',
            parent=base['Heading1'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=14,
            spaceAfter=2,
        ),
        'DaySubheading': ParagraphStyle(
            'DaySubheading',
            parent=base['Normal'],
            fontSize=11,
            leading=14,
            textColor=COLOR_MUTED,
            spaceAfter=8,
        ),
        'ItemLabel': ParagraphStyle(
            'ItemLabel',
            parent=base['Normal'],
            fontSize=8,
            leading=10,
            textColor=COLOR_MUTED,
        ),
        'ItemTitle': ParagraphStyle(
            'ItemTitle',
            parent=base['Normal'],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4,
        ),
        'ItemMeta': ParagraphStyle(
            'ItemMeta',
            parent=base['Normal'],
            fontSize=9,
            leading=12,
            textColor=COLOR_MUTED,
            spaceAfter=3,
        ),
        'ItemBody': ParagraphStyle(
            'ItemBody',
            parent=base['Normal'],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#334155'),
            spaceAfter=4,
        ),
        'Footer': ParagraphStyle(
            'Footer',
            parent=base['Normal'],
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=COLOR_MUTED,
        ),
    }
    apply_fonts_to_styles(styles, body_font)

    story: List = []

    # Cover
    cover_img = _cover_image_flowable(collection)
    if cover_img:
        story.append(Spacer(1, 0.15 * inch))
        story.append(cover_img)
        story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph(pdf_markup(collection.name or 'Trip'), styles['CoverTitle']))

    if collection.start_date and collection.end_date:
        days = _trip_day_count(collection.start_date, collection.end_date)
        date_line = f'{_format_short_date(collection.start_date)} – {_format_short_date(collection.end_date)}'
        if days:
            date_line += f' · {days} day{"s" if days != 1 else ""}'
        story.append(Paragraph(date_line, styles['CoverSubtitle']))
    elif collection.start_date:
        story.append(Paragraph(f'Starts {_format_short_date(collection.start_date)}', styles['CoverSubtitle']))
    else:
        story.append(Paragraph('Trip folder', styles['CoverSubtitle']))

    loc_count = collection.locations.count()
    if loc_count:
        story.append(
            Paragraph(
                f'{loc_count} location{"s" if loc_count != 1 else ""}',
                styles['CoverSubtitle'],
            )
        )

    desc = _plain_text(collection.description)
    if desc:
        story.append(Spacer(1, 0.15 * inch))
        story.append(
            Paragraph(pdf_markup(desc), styles['ItemBody']),
        )

    if collection.link:
        story.append(
            Paragraph(
                f'<link href="{escape_xml(collection.link)}">{pdf_markup(collection.link)}</link>',
                styles['CoverSubtitle'],
            )
        )

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph('Generated by AdventureLog', styles['Footer']))
    story.append(PageBreak())

    if collection.start_date and collection.end_date:
        day_groups, global_items, lookups = _group_itinerary_days(collection)

        if day_groups:
            story.extend(_section_heading('Day-by-day itinerary', styles))
            for day in day_groups:
                day_title = day['display_date']
                if day.get('day_name'):
                    day_title = f'{day["day_name"]} — {day_title}'
                story.append(Paragraph(day_title, styles['DayHeading']))
                if day.get('day_description'):
                    story.append(
                        Paragraph(
                            pdf_markup(day['day_description']),
                            styles['DaySubheading'],
                        )
                    )

                if day.get('overnight_lodging'):
                    names = ', '.join(pdf_markup(l.name) for l in day['overnight_lodging'])
                    story.append(
                        Paragraph(f'<b>Overnight:</b> {names}', styles['DaySubheading']),
                    )

                if not day['items']:
                    story.append(Paragraph('No scheduled items this day.', styles['ItemMeta']))
                    story.append(Spacer(1, 8))
                    continue

                for idx, entry in enumerate(day['items'], start=1):
                    story.extend(
                        _item_card(entry['type'], entry['object'], idx, styles, body_font, emoji_font)
                    )

            if global_items:
                story.append(PageBreak())
                story.extend(_section_heading('Trip-wide items', styles))
                for idx, it in enumerate(sorted(global_items, key=lambda x: x.order), start=1):
                    model, obj = _resolve_item(it, lookups)
                    if obj is not None:
                        story.extend(_item_card(model, obj, idx, styles, body_font, emoji_font))

        else:
            story.extend(_section_heading('Itinerary', styles))
            story.append(
                Paragraph(
                    'No items are scheduled on the itinerary yet. See the reference sections below.',
                    styles['ItemMeta'],
                )
            )
            story.append(Spacer(1, 12))

        scheduled_keys = _scheduled_keys(collection)
        appendix = _folder_sections(
            collection,
            styles,
            body_font,
            emoji_font,
            only_unscheduled=True,
            scheduled_keys=scheduled_keys,
        )
        if appendix:
            story.append(PageBreak())
            story.extend(_section_heading('Additional items (not on itinerary)', styles))
            story.extend(appendix)
    else:
        story.extend(_section_heading('Collection contents', styles))
        story.extend(_folder_sections(collection, styles, body_font, emoji_font))

    doc.build(story)
    return buffer.getvalue()


def pdf_filename_for_collection(collection: Collection) -> str:
    raw = (collection.name or 'collection').strip()
    safe = re.sub(r'[^\w\s-]', '', raw, flags=re.UNICODE)
    safe = re.sub(r'[-\s]+', '_', safe).strip('_') or 'collection'
    return f'{safe}_itinerary.pdf'
