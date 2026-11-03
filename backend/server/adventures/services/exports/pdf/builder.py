"""Putting the sections together into the PDF document."""

from __future__ import annotations

import io
import re
from typing import List
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
from core.formatting import format_short_date
from adventures.models import Collection
from .fonts import (
    apply_fonts_to_styles,
    ensure_pdf_fonts,
    escape_xml,
    pdf_markup,
)

from .theme import COLOR_MUTED, COLOR_PRIMARY
from .text import plain_text
from .data import apply_story_groups, group_itinerary_days, is_day_plan, placed_item_keys, resolve_item, trip_day_count
from .cards import cover_image_flowable, folder_sections, item_card, section_heading


def build_collection_pdf(collection: Collection, story: bool = False) -> bytes:
    """
    Return PDF bytes for the given collection.

    Members get the full plan, including prices and confirmation numbers.
    ``story=True`` is the public reader's copy and follows the story groups.
    """
    if story:
        apply_story_groups(collection)
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
    cover_img = cover_image_flowable(collection)
    if cover_img:
        story.append(Spacer(1, 0.15 * inch))
        story.append(cover_img)
        story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph(pdf_markup(collection.name or 'Trip'), styles['CoverTitle']))

    if collection.start_date and collection.end_date:
        days = trip_day_count(collection.start_date, collection.end_date)
        date_line = f'{format_short_date(collection.start_date)} – {format_short_date(collection.end_date)}'
        if days:
            date_line += f' · {days} day{"s" if days != 1 else ""}'
        story.append(Paragraph(date_line, styles['CoverSubtitle']))
    elif collection.start_date:
        story.append(Paragraph(f'Starts {format_short_date(collection.start_date)}', styles['CoverSubtitle']))
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

    desc = plain_text(collection.description)
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

    if is_day_plan(collection) or (collection.start_date and collection.end_date):
        day_groups, global_items, lookups = group_itinerary_days(collection)

        if day_groups:
            story.extend(section_heading('Day-by-day itinerary', styles))
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
                        item_card(entry['type'], entry['object'], idx, styles, body_font, emoji_font)
                    )

            if global_items:
                story.append(PageBreak())
                story.extend(section_heading('Trip-wide items', styles))
                for idx, it in enumerate(sorted(global_items, key=lambda x: x.order), start=1):
                    model, obj = resolve_item(it, lookups)
                    if obj is not None:
                        story.extend(item_card(model, obj, idx, styles, body_font, emoji_font))

        else:
            story.extend(section_heading('Itinerary', styles))
            story.append(
                Paragraph(
                    'No items are scheduled on the itinerary yet. See the reference sections below.',
                    styles['ItemMeta'],
                )
            )
            story.append(Spacer(1, 12))

        ideas = [
            it for it in collection.itinerary_items.all()
            if is_day_plan(collection) and not it.is_global and it.day_id is None
        ]
        if ideas:
            story.append(PageBreak())
            story.extend(section_heading('Ideas', styles))
            for idx, it in enumerate(sorted(ideas, key=lambda x: x.order), start=1):
                model, obj = resolve_item(it, lookups)
                if obj is not None:
                    story.extend(item_card(model, obj, idx, styles, body_font, emoji_font))

        scheduled_keys = placed_item_keys(collection)
        appendix = folder_sections(
            collection,
            styles,
            body_font,
            emoji_font,
            only_unscheduled=True,
            scheduled_keys=scheduled_keys,
        )
        if appendix:
            story.append(PageBreak())
            story.extend(section_heading('Additional items (not on itinerary)', styles))
            story.extend(appendix)
    else:
        story.extend(section_heading('Collection contents', styles))
        story.extend(folder_sections(collection, styles, body_font, emoji_font))

    doc.build(story)
    return buffer.getvalue()


def pdf_filename_for_collection(collection: Collection) -> str:
    raw = (collection.name or 'collection').strip()
    safe = re.sub(r'[^\w\s-]', '', raw, flags=re.UNICODE)
    safe = re.sub(r'[-\s]+', '_', safe).strip('_') or 'collection'
    return f'{safe}_itinerary.pdf'
