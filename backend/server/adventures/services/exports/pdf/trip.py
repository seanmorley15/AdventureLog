"""The Trip Book: cover, overview map, essentials, one page per day, and an index."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from reportlab.platypus import KeepTogether, NextPageTemplate, PageBreak, Paragraph, Spacer

from adventures.models import Collection

from .components import (
    category_text,
    day_band,
    entry_table,
    entry_time,
    geo_text,
    grid_table,
    legend,
    map_flowable,
    point_latlon,
    section_heading,
    stat_strip,
)
from .data import (
    cost_summary,
    group_itinerary_days,
    is_day_plan,
    placed_item_keys,
    resolve_item,
    travelers,
    trip_day_count,
)
from .fonts import pdf_markup
from .layout import HERO_HEIGHT, Anchor, Ctx, EndMarker, cover_date_line, render_book
from .maps import MapLeg, MapPoint, MapRenderer
from .media import MediaCache
from .options import PdfOptions
from .text import body_paragraphs, format_datetime, format_money
from .theme import build_styles, day_color
from .writein import RuledLines

OVERVIEW_MAP_HEIGHT = 250
DAY_MAP_HEIGHT = 170


def _pins(model: str, obj: Any) -> List[Tuple[float, float]]:
    """Where an entry is on the map: a place or stay is one point, transport is where it starts and ends."""
    if model in ('location', 'lodging'):
        latlon = point_latlon(obj.coordinates)
        return [latlon] if latlon else []
    if model == 'transportation':
        return [p for p in (point_latlon(obj.origin), point_latlon(obj.destination)) if p]
    return []


def map_data(entries: List[Tuple[str, Any, str, str]], transport: str = 'auto') -> Tuple[List[MapPoint], List[MapLeg]]:
    """
    Pins and the route for entries given as (model, object, pin label, colour), in order.
    Stops are joined by a solid line; the stretch a transport covers is dashed.

    A flight from far away would shrink the places that matter to dots, so with ``transport``
    set to ``auto`` it is drawn only when there is nothing else to show; ``never`` leaves it out.
    """
    stops = [e for e in entries if e[0] != 'transportation' and _pins(e[0], e[1])]
    if transport == 'never' or (transport == 'auto' and stops):
        entries = stops
    points: List[MapPoint] = []
    legs: List[MapLeg] = []
    previous: Optional[Tuple[float, float]] = None
    for model, obj, label, color in entries:
        coords = _pins(model, obj)
        for index, latlon in enumerate(coords):
            points.append(MapPoint(latlon[0], latlon[1], label, color))
            if previous and previous != latlon:
                dashed = model == 'transportation' and index == 1
                legs.append(MapLeg(previous, latlon, dashed=dashed))
            previous = latlon
    return points, legs


def _countries(collection: Collection) -> List[str]:
    seen: List[str] = []
    for location in collection.locations.all():
        if location.country and location.country.name not in seen:
            seen.append(location.country.name)
    return seen


def _nights(collection: Collection, days: Optional[int]) -> Optional[int]:
    if collection.start_date and collection.end_date:
        return max((collection.end_date - collection.start_date).days, 0)
    return max(days - 1, 0) if days else None


def build_trip_book(collection: Collection, options: PdfOptions, story: bool = False) -> bytes:
    styles = build_styles()
    media = MediaCache(enabled=options.photos)
    maps = MapRenderer()
    width = options.pagesize[0]
    hero = media.cover(collection, width, HERO_HEIGHT)

    day_groups, global_items, lookups = group_itinerary_days(collection) if (
        is_day_plan(collection) or (collection.start_date and collection.end_date)
    ) else ([], [], None)
    has_plan = bool(day_groups)

    def make_story(refs: Dict[str, int], total: int) -> List:
        ctx = Ctx(collection=collection, options=options, story=story, styles=styles,
                  width=width - 80, media=media, maps=maps, refs=refs, total_pages=total)
        out: List = []
        out.extend(_cover(ctx, day_groups))
        numbering: Dict[str, List[int]] = defaultdict(list)
        out.extend(_overview(ctx, day_groups))
        out.extend(_essentials(ctx))
        out.extend(_days(ctx, day_groups, numbering))
        out.extend(_extras(ctx, day_groups, global_items, lookups, has_plan))
        out.extend(_place_index(ctx, numbering))
        out.extend(_notes_pages(ctx))
        while out and isinstance(out[-1], PageBreak):
            out.pop()  # No blank page at the end.
        out.append(EndMarker())
        return out

    return render_book(
        options,
        title=collection.name or 'Trip',
        kind_label='Trip Book',
        footer_text=collection.name or 'Trip',
        hero=hero,
        make_story=make_story,
    )


# --- cover -----------------------------------------------------------------------------------


def _cover(ctx: Ctx, day_groups: List[Dict[str, Any]]) -> List:
    c, s = ctx.collection, ctx.styles
    out: List = []
    countries = _countries(c)
    out.append(Paragraph(pdf_markup(' · '.join(countries).upper() if countries else 'TRIP'), s['CoverKicker']))
    out.append(Paragraph(pdf_markup(c.name or 'Trip'), s['CoverTitle']))
    out.append(Spacer(1, 8))

    days = trip_day_count(c.start_date, c.end_date) or (len(day_groups) or None)
    nights = _nights(c, days)
    date_line = cover_date_line(c.start_date, c.end_date)
    if date_line:
        out.append(Paragraph(pdf_markup(date_line), s['CoverDates']))
    elif days:
        out.append(Paragraph(f'{days} day{"s" if days != 1 else ""}', s['CoverDates']))
    out.append(Spacer(1, 12))

    stats = stat_strip(ctx, [
        (str(days) if days else '', 'Days'),
        (str(nights) if nights is not None and date_line else '', 'Nights'),
        (str(c.locations.count()) if c.locations.count() else '', 'Places'),
        (str(len(c.lodging_set.all())) if c.lodging_set.all() else '', 'Stays'),
        (str(len(c.transportation_set.all())) if c.transportation_set.all() else '', 'Transport'),
    ])
    if stats:
        out.append(stats)
        out.append(Spacer(1, 14))
    out.extend(body_paragraphs(c.description, s['CoverBody'], max_length=700))
    if not ctx.story:
        people = travelers(c)
        if len(people) > 1:
            out.append(Spacer(1, 6))
            out.append(Paragraph('<b>Travelers</b>  ' + pdf_markup(', '.join(people)), s['CoverBody']))
    out.append(NextPageTemplate('body'))
    out.append(PageBreak())
    return out


# --- overview and contents ---------------------------------------------------------------------


def _day_label(day: Dict[str, Any], number: int) -> Tuple[str, str]:
    """(kicker, title) of a day's header."""
    d = day['date']
    kicker = f'DAY {number}'
    if d:
        kicker += f'  ·  {d:%A}, {d:%b} {d.day}'.upper()
    if day['day_name']:
        return kicker, day['day_name']
    if d:
        return f'DAY {number}', f'{d:%A, %B} {d.day}'
    return kicker, f'Day {number}'


def _overview(ctx: Ctx, day_groups: List[Dict[str, Any]]) -> List:
    s = ctx.styles
    out: List = [Anchor('overview', 'Overview'), Paragraph('Overview', s['PageTitle']), Spacer(1, 6)]

    entries = []
    for number, day in enumerate(day_groups, start=1):
        for entry in day['items']:
            entries.append((entry['type'], entry['object'], str(number), day_color(number - 1)))
    points, legs = map_data(entries, transport='never')
    if not points:
        # Nothing scheduled with a position: fall back to every place the trip has.
        fallback = [('location', loc, '', '#0d9488') for loc in ctx.collection.locations.all()]
        points, legs = map_data(fallback)
        legs = []
    picture = map_flowable(ctx, points, OVERVIEW_MAP_HEIGHT, legs)
    if picture:
        out.append(picture)
        out.append(Spacer(1, 6))
        key = legend(ctx, [(str(n), day_color(n - 1), f'Day {n}') for n in range(1, len(day_groups) + 1)][:12], per_row=6)
        if key and day_groups:
            out.append(key)
        out.append(Spacer(1, 10))

    if day_groups:
        rows = []
        for number, day in enumerate(day_groups, start=1):
            d = day['date']
            date_text = f'{d:%a}, {d:%b} {d.day}' if d else ''
            names = [pdf_markup(e['object'].name) for e in day['items'] if getattr(e['object'], 'name', None)]
            plan = f'<b>{pdf_markup(day["day_name"])}</b>  ' if day['day_name'] else ''
            plan += ' · '.join(names[:4]) + (f' · +{len(names) - 4} more' if len(names) > 4 else '')
            page = f'<link href="#day-{number}" color="#0f766e">p. {ctx.page_of(f"day-{number}")}</link>'
            rows.append([
                Paragraph(f'<b>Day {number}</b>', s['TableCellBold']),
                date_text,
                Paragraph(plan or '<font color="#94a3b8">Nothing planned yet</font>', s['TableCell']),
                Paragraph(page, s['TableCellRight']),
            ])
        out.append(grid_table(ctx, ['Day', 'Date', 'Plan', 'Page'], rows, [9, 14, 52, 7]))
    else:
        out.append(Paragraph('Nothing is scheduled on a day yet. Everything in the trip is listed at the end of this book.', s['Hint']))
    out.append(PageBreak())
    return out


# --- essentials ------------------------------------------------------------------------------


def _essentials(ctx: Ctx) -> List:
    c, s = ctx.collection, ctx.styles
    transport = sorted(c.transportation_set.all(), key=lambda t: (t.date is None, t.date))
    stays = sorted(c.lodging_set.all(), key=lambda l: (l.check_in is None, l.check_in))
    costs = cost_summary(c)
    if not (transport or stays or costs):
        return []

    out: List = [Anchor('essentials', 'Essentials'), Paragraph('Essentials', s['PageTitle']),
                 Paragraph('Bookings and costs in one place.', s['Hint'])]

    if transport:
        out.extend(section_heading(ctx, 'Getting there'))
        rows = []
        for t in transport:
            codes = ' to '.join(x for x in (t.start_code, t.end_code) if x)
            places = ' to '.join(x for x in (t.from_location, t.to_location) if x)
            route = f'<b>{pdf_markup(codes)}</b><br/>{pdf_markup(places)}' if codes else pdf_markup(places or t.name or '')
            when = pdf_markup(format_datetime(t.date, t.start_timezone))
            if t.end_date:
                when += '<br/>' + pdf_markup('Arrives ' + format_datetime(t.end_date, t.end_timezone))
            kind = (t.type or '').replace('_', ' ').title()
            details = pdf_markup(' · '.join(x for x in (t.name, kind, t.flight_number) if x))
            rows.append([Paragraph(when, s['TableCell']), Paragraph(route, s['TableCell']), Paragraph(details, s['TableCell'])])
        out.append(grid_table(ctx, ['When', 'Route', 'Details'], rows, [24, 40, 36]))

    if stays:
        out.extend(section_heading(ctx, 'Where you are staying'))
        rows = []
        for stay in stays:
            name = f'<b>{pdf_markup(stay.name)}</b>'
            rows.append([
                Paragraph(name, s['TableCell']),
                Paragraph(pdf_markup(format_datetime(stay.check_in, stay.timezone)), s['TableCell']) if stay.check_in else '',
                Paragraph(pdf_markup(format_datetime(stay.check_out, stay.timezone)), s['TableCell']) if stay.check_out else '',
                Paragraph(pdf_markup(stay.location or ''), s['TableCell']),
                Paragraph(f'<b>{pdf_markup(stay.reservation_number)}</b>' if stay.reservation_number else '', s['TableCell']),
            ])
        out.append(grid_table(ctx, ['Stay', 'Check-in', 'Check-out', 'Address', 'Confirmation'], rows, [20, 20, 20, 22, 18]))

    if costs:
        out.extend(section_heading(ctx, 'What it costs'))
        for bucket in costs:
            rows = [[line['label'], Paragraph(f'{line["count"]} item{"s" if line["count"] != 1 else ""}', s['TableCellRight']),
                     Paragraph(pdf_markup(format_money(line['total'], bucket['currency'])), s['TableCellRight'])] for line in bucket['lines']]
            rows.append([Paragraph('<b>Total</b>', s['TableCell']), '',
                         Paragraph(f'<b>{pdf_markup(format_money(bucket["total"], bucket["currency"]))}</b>', s['TableCellRight'])])
            out.append(KeepTogether([grid_table(ctx, ['Spent on', '', bucket['currency']], rows, [50, 20, 30]), Spacer(1, 8)]))
    out.append(PageBreak())
    return out


# --- the days --------------------------------------------------------------------------------


def _days(ctx: Ctx, day_groups: List[Dict[str, Any]], numbering: Dict[str, List[int]]) -> List:
    out: List = []
    s = ctx.styles
    for number, day in enumerate(day_groups, start=1):
        color = day_color(number - 1)
        kicker, title = _day_label(day, number)
        out.append(Anchor(f'day-{number}', f'Day {number}' + (f' – {day["day_name"]}' if day['day_name'] else '')))
        out.append(day_band(ctx, number, color, kicker, title, day['day_description'], day['overnight_lodging']))
        out.append(Spacer(1, 10))

        entries = [(e['type'], e['object'], str(i), color) for i, e in enumerate(day['items'], start=1)]
        points, legs = map_data(entries)
        picture = map_flowable(ctx, points, DAY_MAP_HEIGHT, legs)
        if picture:
            out.append(picture)
            out.append(Spacer(1, 12))

        if not day['items']:
            out.append(Paragraph('Nothing planned for this day.', s['Hint']))
            out.append(Spacer(1, 8))
        for index, entry in enumerate(day['items'], start=1):
            model, obj, item = entry['type'], entry['object'], entry.get('item')
            if model == 'location':
                numbering[str(obj.id)].append(number)
            time_text, time_sub = entry_time(model, obj, item)
            out.extend(entry_table(ctx, model, obj, number=index, time_text=time_text, time_sub=time_sub,
                                   optional=bool(getattr(item, 'is_optional', False))))
        if ctx.options.journal:
            out.append(Spacer(1, 6))
            out.append(RuledLines(ctx.width, label='Notes from the day', spacing=22, min_height=90, max_height=320))
        out.append(PageBreak())
    return out


# --- everything that is not on a day -------------------------------------------------------------


def _list_section(ctx: Ctx, key: str, title: str, hint: str, pairs: List[Tuple[str, Any]]) -> List:
    if not pairs:
        return []
    out: List = [Anchor(key, title), Paragraph(pdf_markup(title), ctx.styles['PageTitle']), Paragraph(pdf_markup(hint), ctx.styles['Hint']), Spacer(1, 8)]
    for number, (model, obj) in enumerate(pairs, start=1):
        out.extend(entry_table(ctx, model, obj, number=number))
    out.append(PageBreak())
    return out


def _extras(ctx: Ctx, day_groups, global_items, lookups, has_plan: bool) -> List:
    c = ctx.collection
    out: List = []
    if has_plan:
        wide = []
        for item in sorted(global_items, key=lambda x: x.order):
            model, obj = resolve_item(item, lookups)
            if obj is not None:
                wide.append((model, obj))
        out.extend(_list_section(ctx, 'trip-wide', 'Trip-wide', 'Applies to the whole trip, not one day.', wide))

        if is_day_plan(c):
            ideas = []
            for item in sorted((i for i in c.itinerary_items.all() if not i.is_global and i.day_id is None), key=lambda x: x.order):
                model, obj = resolve_item(item, lookups)
                if obj is not None:
                    ideas.append((model, obj))
            out.extend(_list_section(ctx, 'ideas', 'Ideas', 'Not planned yet, but worth considering.', ideas))

    scheduled = placed_item_keys(c)
    rest = []
    for model, items in (('location', c.locations.all()), ('transportation', c.transportation_set.all()),
                         ('lodging', c.lodging_set.all()), ('note', c.note_set.all()), ('checklist', c.checklist_set.all())):
        rest.extend((model, obj) for obj in items if (model, str(obj.id)) not in scheduled)
    title, hint = ('Also in this trip', 'Saved with the trip but not on a day.') if has_plan else ('In this trip', 'Everything saved with the trip.')
    out.extend(_list_section(ctx, 'unscheduled', title, hint, rest))
    return out


# --- index and blank notes -------------------------------------------------------------------


def _place_index(ctx: Ctx, numbering: Dict[str, List[int]]) -> List:
    s = ctx.styles
    locations = sorted(ctx.collection.locations.all(), key=lambda l: (l.name or '').lower())
    if not locations:
        return []
    rows = []
    for loc in locations:
        days = numbering.get(str(loc.id), [])
        day_links = ', '.join(f'<link href="#day-{n}" color="#0f766e">Day {n} (p. {ctx.page_of(f"day-{n}")})</link>' for n in sorted(set(days)))
        where = ' · '.join(x for x in (category_text(loc), geo_text(loc)) if x)
        rows.append([
            Paragraph(f'<b>{pdf_markup(loc.name)}</b>', s['TableCell']),
            Paragraph(pdf_markup(where), s['TableCell']),
            Paragraph(day_links or '<font color="#94a3b8">not on a day</font>', s['TableCell']),
        ])
    return [Anchor('index', 'Place index'), Paragraph('Place index', s['PageTitle']), Spacer(1, 6),
            grid_table(ctx, ['Place', 'Where', 'When'], rows, [34, 34, 32]), PageBreak()]


def _notes_pages(ctx: Ctx) -> List:
    if not ctx.options.journal:
        return []
    out: List = []
    for page in range(2):
        out.append(Anchor(f'notes-{page + 1}', 'Notes' if page == 0 else None))
        out.append(RuledLines(ctx.width, label='Notes', spacing=24))
        if page == 0:
            out.append(PageBreak())
    return out
