"""The cards, headings and sections the itinerary is made of."""

from __future__ import annotations

import io
from typing import Any, List, Optional
from PIL import Image as PILImage
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle
from core.formatting import format_short_date
from adventures.models import Checklist, Collection, Location, Lodging, Note, Transportation
from .fonts import escape_xml, pdf_markup

from .theme import COLOR_BORDER, COLOR_LIGHT_BG, COLOR_MUTED
from .text import NOTE_PDF_MAX_LENGTH, body_paragraphs, format_datetime, format_money


# Minimum leftover height (points) required to split a card mid-row.
_CARD_SPLIT_IN_ROW = 40


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

    # Visits are the place's own log and are not part of a published story.
    visits = [] if getattr(location, '_story_hide_visits', False) else location.visits.all().order_by('start_date')
    for visit in visits:
        start = visit.start_date.date() if visit.start_date else None
        end = visit.end_date.date() if visit.end_date else None
        if start and end and end != start:
            flowables.append(
                Paragraph(
                    f'Visit: {format_short_date(start)} – {format_short_date(end)}',
                    styles['ItemMeta'],
                )
            )
        elif start:
            flowables.append(Paragraph(f'Visit: {format_short_date(start)}', styles['ItemMeta']))

    flowables.extend(body_paragraphs(location.description, styles['ItemBody']))

    extras = []
    if location.rating is not None:
        extras.append(f'Rating: {location.rating}/5')
    if location.price is not None:
        extras.append(format_money(location.price.amount, str(location.price.currency)))
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
        line = format_datetime(transport.date, transport.start_timezone)
        if transport.end_date:
            line += f' – {format_datetime(transport.end_date, transport.end_timezone)}'
        flowables.append(Paragraph(line, styles['ItemMeta']))

    if transport.flight_number:
        flowables.append(Paragraph(f'Flight: {pdf_markup(transport.flight_number)}', styles['ItemMeta']))

    flowables.extend(body_paragraphs(transport.description, styles['ItemBody']))

    extras = []
    if transport.rating is not None:
        extras.append(f'Rating: {transport.rating}/5')
    if transport.price is not None:
        extras.append(format_money(transport.price, transport.price_currency))
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
        check_in = format_datetime(lodging.check_in, lodging.timezone) if lodging.check_in else '—'
        check_out = format_datetime(lodging.check_out, lodging.timezone) if lodging.check_out else '—'
        flowables.append(Paragraph(f'Check-in: {check_in} · Check-out: {check_out}', styles['ItemMeta']))
    if lodging.reservation_number:
        flowables.append(Paragraph(f'Confirmation: {pdf_markup(lodging.reservation_number)}', styles['ItemMeta']))

    flowables.extend(body_paragraphs(lodging.description, styles['ItemBody']))

    extras = []
    if lodging.rating is not None:
        extras.append(f'Rating: {lodging.rating}/5')
    if lodging.price is not None:
        extras.append(format_money(lodging.price, lodging.price_currency))
    if lodging.link:
        extras.append(f'<link href="{escape_xml(lodging.link)}">Link</link>')
    if extras:
        flowables.append(Paragraph(' · '.join(extras), styles['ItemMeta']))

    return flowables


def _note_paragraphs(note: Note, styles) -> List:
    flowables = []
    flowables.append(Paragraph(f'<b>{pdf_markup(note.name or "Note")}</b>', styles['ItemTitle']))
    if note.date:
        flowables.append(Paragraph(format_short_date(note.date), styles['ItemMeta']))
    flowables.extend(
        body_paragraphs(note.content, styles['ItemBody'], max_length=NOTE_PDF_MAX_LENGTH)
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
        flowables.append(Paragraph(format_short_date(checklist.date), styles['ItemMeta']))
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


def item_card(
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


def cover_image_flowable(collection: Collection, max_width: float = 6.5 * inch) -> Optional[Image]:
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


def section_heading(text: str, styles) -> List:
    return [
        Paragraph(text, styles['SectionHeading']),
        Spacer(1, 8),
    ]


def folder_sections(
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
        story.extend(section_heading(heading, styles))
        for obj in items:
            story.extend(item_card(model, obj, order, styles, body_font, emoji_font))
            order += 1
    return story
