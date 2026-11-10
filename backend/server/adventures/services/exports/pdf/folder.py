"""The Field Guide: a workbook for a folder of places, with boxes to tick and lines to write on."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from reportlab.platypus import KeepTogether, NextPageTemplate, PageBreak, Paragraph, Spacer, Table, TableStyle

from adventures.models import Collection

from .components import (
    entry_table,
    geo_text,
    grid_table,
    legend,
    map_flowable,
    place_text,
    point_latlon,
    section_heading,
    side_column,
    stat_strip,
)
from .data import travelers, visit_info
from .fonts import pdf_markup, renderable_icon
from .layout import HERO_HEIGHT, Anchor, Ctx, EndMarker, render_book
from .maps import MapPoint, MapRenderer
from .media import MediaCache
from .options import PdfOptions
from .text import body_paragraphs
from .theme import CATEGORY_COLORS, build_styles, hex_color
from .writein import Checkbox, FillIn, FilledRating, Marker, ProgressBar, RatingCircles, RuledLines
from core.formatting import format_short_date

DESCRIPTION_MAX = 600
SIDE_WIDTH = 104
OVERVIEW_MAP_HEIGHT = 270


class Group:
    def __init__(self, title: str, icon: str, color: str, places: List[Any]):
        self.title, self.icon, self.color, self.places = title, icon, color, places


def group_places(locations: List[Any]) -> List[Group]:
    """
    Put places under headings: by category when there are at least two, else by country, else
    in one list. Places keep a stable order (by name) so numbers match from map to entry.
    """
    def by(key_fn, icon_fn=lambda loc: '') -> Optional[List[Group]]:
        buckets: Dict[str, List[Any]] = {}
        icons: Dict[str, str] = {}
        for loc in locations:
            key = key_fn(loc) or 'Other'
            buckets.setdefault(key, []).append(loc)
            icons.setdefault(key, icon_fn(loc))
        if len(buckets) < 2:
            return None
        ordered = sorted(buckets, key=lambda k: (k == 'Other', k.lower()))
        return [Group(k, icons.get(k, ''), CATEGORY_COLORS[i % len(CATEGORY_COLORS)],
                      sorted(buckets[k], key=lambda l: (l.name or '').lower())) for i, k in enumerate(ordered)]

    def category_name(loc):
        return (loc.category.display_name or loc.category.name) if loc.category else ''

    groups = (
        by(category_name, lambda loc: renderable_icon(loc.category.icon or '') if loc.category else '')
        or by(lambda loc: loc.country.name if loc.country else '')
    )
    if groups:
        return groups
    return [Group('Places', '', CATEGORY_COLORS[0], sorted(locations, key=lambda l: (l.name or '').lower()))]


def build_field_guide(collection: Collection, options: PdfOptions, story: bool = False) -> bytes:
    styles = build_styles()
    media = MediaCache(enabled=options.photos)
    maps = MapRenderer()
    width = options.pagesize[0]
    hero = media.cover(collection, width, HERO_HEIGHT)
    locations = list(collection.locations.all())
    groups = group_places(locations) if locations else []
    numbers: Dict[str, Tuple[int, Group]] = {}
    position = 1
    for group in groups:
        for loc in group.places:
            numbers[str(loc.id)] = (position, group)
            position += 1

    def make_story(refs: Dict[str, int], total: int) -> List:
        ctx = Ctx(collection=collection, options=options, story=story, styles=styles,
                  width=width - 80, media=media, maps=maps, refs=refs, total_pages=total)
        out: List = []
        out.extend(_cover(ctx, groups))
        out.extend(_overview(ctx, groups, numbers))
        out.extend(_entries(ctx, groups, numbers))
        out.extend(_other_items(ctx))
        out.extend(_places_to_add(ctx))
        while out and isinstance(out[-1], PageBreak):
            out.pop()
        out.append(EndMarker())
        return out

    return render_book(
        options,
        title=collection.name or 'Folder',
        kind_label='Field Guide',
        footer_text=collection.name or 'Folder',
        hero=hero,
        make_story=make_story,
    )


# --- cover ---------------------------------------------------------------------------------


def _cover(ctx: Ctx, groups: List[Group]) -> List:
    c, s = ctx.collection, ctx.styles
    places = [loc for g in groups for loc in g.places]
    visited = sum(1 for loc in places if visit_info(loc)[0]) if ctx.show_visits else 0
    countries = []
    for loc in places:
        if loc.country and loc.country.name not in countries:
            countries.append(loc.country.name)

    out: List = [Paragraph(pdf_markup(' · '.join(countries[:4]).upper() if countries else 'FOLDER'), s['CoverKicker']),
                 Paragraph(pdf_markup(c.name or 'Folder'), s['CoverTitle']), Spacer(1, 10)]
    if places:
        line = f'{len(places)} place{"s" if len(places) != 1 else ""}'
        if ctx.show_visits:
            line += f'  ·  {visited} visited'
        out.append(Paragraph(pdf_markup(line), s['CoverDates']))
        if ctx.show_visits:
            out.append(Spacer(1, 4))
            out.append(ProgressBar(ctx.width, visited / len(places)))
        out.append(Spacer(1, 14))
    stats = stat_strip(ctx, [
        (str(len(places)) if places else '', 'Places'),
        (str(visited) if places and ctx.show_visits else '', 'Visited'),
        (str(len(groups)) if len(groups) > 1 else '', 'Groups'),
        (str(len(c.note_set.all()) + len(c.checklist_set.all())) if (c.note_set.all() or c.checklist_set.all()) else '', 'Notes & lists'),
    ])
    if stats:
        out.extend([stats, Spacer(1, 14)])
    out.extend(body_paragraphs(c.description, s['CoverBody'], max_length=700))
    if not ctx.story:
        people = travelers(c)
        if len(people) > 1:
            out.extend([Spacer(1, 6), Paragraph('<b>Shared with</b>  ' + pdf_markup(', '.join(people[1:])), s['CoverBody'])])
    out.extend([NextPageTemplate('body'), PageBreak()])
    return out


# --- overview map and checklist index --------------------------------------------------------


def _overview(ctx: Ctx, groups: List[Group], numbers: Dict[str, Tuple[int, Group]]) -> List:
    s = ctx.styles
    places = [loc for g in groups for loc in g.places]
    if not places:
        return []
    out: List = [Anchor('overview', 'Overview'), Paragraph('Overview', s['PageTitle'])]
    if ctx.options.journal:
        out.append(Paragraph('Tick a place when you have been, write the date, and colour in how much you liked it.', s['Hint']))
    out.append(Spacer(1, 6))

    points = []
    for loc in places:
        latlon = point_latlon(loc.coordinates)
        if latlon:
            number, group = numbers[str(loc.id)]
            points.append(MapPoint(latlon[0], latlon[1], str(number), group.color))
    picture = map_flowable(ctx, points, OVERVIEW_MAP_HEIGHT)
    if picture:
        out.append(picture)
        out.append(Spacer(1, 6))
        if len(groups) > 1:
            key = legend(ctx, [(' ', g.color, f'{g.icon} {g.title} ({len(g.places)})'.strip()) for g in groups], per_row=3)
            if key:
                out.append(key)
        out.append(Spacer(1, 10))

    out.extend(section_heading(ctx, 'Checklist'))
    rows = []
    for loc in places:
        number, group = numbers[str(loc.id)]
        visited, _ = visit_info(loc)
        page = f'<link href="#place-{loc.id}" color="#0f766e">p. {ctx.page_of(f"place-{loc.id}")}</link>'
        rows.append([
            Checkbox(10, checked=visited),
            Paragraph(f'<b>{number}</b>', s['TableCell']),
            Paragraph(f'<b>{pdf_markup(loc.name)}</b>', s['TableCell']),
            Paragraph(pdf_markup(geo_text(loc) or loc.location or ''), s['TableCell']),
            Paragraph(page, s['TableCellRight']),
        ])
    out.append(grid_table(ctx, ['', '#', 'Place', 'Where', 'Page'], rows, [5, 6, 42, 38, 9]))
    out.append(PageBreak())
    return out


# --- one entry per place -----------------------------------------------------------------------


def _write_strip(ctx: Ctx, loc: Any, visited: bool, last_visit) -> Table:
    """"Visited on ____ Rating ○○○○○" and a few lines for notes."""
    s = ctx.styles
    prefill = format_short_date(last_visit) if visited and last_visit else ''
    rating = FilledRating(loc.rating, size=9, gap=4) if loc.rating is not None else RatingCircles(5, size=9, gap=4)
    inner_w = ctx.width - 34 - SIDE_WIDTH - 12
    row = Table([[Paragraph('VISITED ON', s['WriteLabel']), FillIn(110, prefill), Paragraph('RATING', s['WriteLabel']), rating]],
                colWidths=[56, 118, 42, None])
    row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    strip = Table([[row], [RuledLines(inner_w + SIDE_WIDTH + 12, count=3, spacing=19, label='Notes')]],
                  colWidths=[ctx.width - 34])
    strip.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return strip


def _place_entry(ctx: Ctx, loc: Any, number: int, group: Group, lead: List) -> List:
    visited, last_visit = visit_info(loc)
    text = place_text(ctx, loc, description_max=DESCRIPTION_MAX, category=False, visits=False)
    side = side_column(ctx, 'location', loc, SIDE_WIDTH)
    badge = [Marker(str(number), group.color, 22), Spacer(1, 8), Checkbox(14, checked=visited, color=hex_color(group.color))]
    rows = [[badge, text, side or '']]
    spans = []
    if ctx.options.journal:
        rows.append(['', _write_strip(ctx, loc, visited, last_visit), ''])
        spans.append(('SPAN', (1, 1), (2, 1)))
    table = Table(rows, colWidths=[34, ctx.width - 34 - SIDE_WIDTH, SIDE_WIDTH])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, hex_color('#e2e8f0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
        *spans,
    ]))
    return [KeepTogether([*lead, Anchor(f'place-{loc.id}'), table, Spacer(1, 8)])]


def _entries(ctx: Ctx, groups: List[Group], numbers: Dict[str, Tuple[int, Group]]) -> List:
    s = ctx.styles
    out: List = []
    for group in groups:
        for index, loc in enumerate(group.places):
            lead: List = []
            if index == 0:
                title = f'{group.icon} {group.title}'.strip()
                head = Table([[Paragraph(pdf_markup(title), s['GroupHeading']),
                               Paragraph(f'{len(group.places)} place{"s" if len(group.places) != 1 else ""}', s['TableCellRight'])]],
                             colWidths=[ctx.width * 0.75, ctx.width * 0.25])
                head.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                    ('LINEBELOW', (0, 0), (-1, 0), 2, hex_color(group.color)),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                lead = [Anchor(f'group-{group.title}', title, level=0) if len(groups) > 1 else Anchor('places', 'Places'), head, Spacer(1, 10)]
            number, _ = numbers[str(loc.id)]
            out.extend(_place_entry(ctx, loc, number, group, lead))
    return out


# --- everything else the folder holds ----------------------------------------------------------


def _other_items(ctx: Ctx) -> List:
    c = ctx.collection
    out: List = []
    for key, title, model, items in (
        ('notes', 'Notes', 'note', c.note_set.all()),
        ('checklists', 'Checklists', 'checklist', c.checklist_set.all()),
        ('transport', 'Transport', 'transportation', c.transportation_set.all()),
        ('stays', 'Stays', 'lodging', c.lodging_set.all()),
    ):
        items = list(items)
        if not items:
            continue
        out.append(PageBreak())
        out.append(Anchor(key, title))
        out.append(Paragraph(pdf_markup(title), ctx.styles['PageTitle']))
        out.append(Spacer(1, 6))
        for obj in items:
            out.extend(entry_table(ctx, model, obj))
    return out


def _places_to_add(ctx: Ctx) -> List:
    if not ctx.options.journal:
        return []
    s = ctx.styles
    out: List = [PageBreak(), Anchor('to-add', 'Places to add'), Paragraph('Places to add', s['PageTitle']),
                 Paragraph('Room for the places you find along the way.', s['Hint']), Spacer(1, 10)]
    half = (ctx.width - 40) * 0.5
    rows = [[Checkbox(11), FillIn(half, height=24), FillIn(half, height=24)] for _ in range(14)]
    table = Table([[Paragraph('', s['TableHead']), Paragraph('PLACE', s['WriteLabel']), Paragraph('WHERE / NOTES', s['WriteLabel'])], *rows],
                  colWidths=[24, half + 8, half + 8])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    out.append(table)
    return out
