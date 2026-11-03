"""
Finding the regions of one country that are really a country of their own in the dataset.

The world dataset lists Guadeloupe both as a country and as a French overseas region, Puerto
Rico both as a country and as a US outlying area, and so on. A geocoder reports such a place
under its parent, so the two entries have to be tied together. Nothing here names a place:
the tie is worked out from the dataset's own fields, so it follows the data when it changes.
Pure: no database, no network.
"""

from collections import Counter, defaultdict

from core.geo import distance_km
from worldtravel.naming import name_keys, name_words, normalize_name


def _name_variants(*names):
    return [name for name in names if name]


def find_territory_links(countries, regions):
    """
    Map each region that is also a country to that country's code.

    ``countries`` are dicts with ``code``, ``name``, ``native``, ``lat`` and ``lon``;
    ``regions`` are dicts with ``id``, ``country`` (its country's code), ``name``, ``native``,
    ``type``, ``lat`` and ``lon``. Returns ``{region_id: country_code}``.

    A region is linked when all of these hold:

    1. Its type differs from the most common type in its own country. Overseas regions among
       departments are linked. A province named like another country ("Luxembourg" in
       Belgium) is an ordinary province, so it is not.
    2. It matches exactly one other country, by name or native name, or by a code ending that
       is that country's code while the names share a word.
    3. Unless the whole name matches, it is closer to that country's centre than to the
       centre of its own country. This keeps "Norfolk" in England apart from Norfolk Island.
    """
    by_code = {country['code']: country for country in countries}
    keys_to_countries = defaultdict(set)
    exact_to_countries = defaultdict(set)
    for country in by_code.values():
        for name in _name_variants(country['name'], country.get('native')):
            exact_to_countries[normalize_name(name)].add(country['code'])
            for key in name_keys(name):
                keys_to_countries[key].add(country['code'])

    regions_by_country = defaultdict(list)
    for region in regions:
        regions_by_country[region['country']].append(region)

    links = {}
    for code, own_regions in regions_by_country.items():
        own = by_code.get(code)
        if own is None or len(own_regions) < 2:
            continue
        common_type = Counter((region.get('type') or '') for region in own_regions).most_common(1)[0][0]

        for region in own_regions:
            if (region.get('type') or '') == common_type:
                continue
            names = _name_variants((region['name'] or '').strip(), region.get('native'))
            candidates, whole_name = set(), set()
            for name in names:
                whole_name |= exact_to_countries.get(normalize_name(name), set())
                for key in name_keys(name):
                    candidates |= keys_to_countries.get(key, set())
            candidates.discard(code)
            whole_name.discard(code)

            suffix = region['id'].split('-', 1)[1] if '-' in region['id'] else ''
            if suffix in by_code and suffix != code:
                if suffix in candidates or name_words(region['name']) & name_words(by_code[suffix]['name']):
                    candidates = {suffix}

            def closer_than_parent(other_code):
                if region.get('lat') is None or region.get('lon') is None:
                    return False
                other = by_code[other_code]
                if other.get('lat') is None or own.get('lat') is None:
                    return False
                return (
                    distance_km(region['lat'], region['lon'], other['lat'], other['lon'])
                    < distance_km(region['lat'], region['lon'], own['lat'], own['lon'])
                )

            accepted = {c for c in candidates if c in whole_name or closer_than_parent(c)}
            if len(accepted) == 1:
                links[region['id']] = accepted.pop()
    return links


def pair_cities(parent_cities, territory_cities):
    """
    Pairs of city ids, one from the parent's region and one from the territory, that are the same place.

    ``parent_cities`` and ``territory_cities`` are ``(id, name)`` rows. A pair needs the same name
    once on each side: two cities named alike in one place cannot be told apart. Returns
    ``[(parent_city_id, territory_city_id)]``.
    """

    def by_name(rows):
        found = defaultdict(list)
        for city_id, name in rows:
            key = normalize_name(name or '')
            if key:
                found[key].append(city_id)
        return found

    parents, territory = by_name(parent_cities), by_name(territory_cities)
    return [
        (ids[0], territory[key][0])
        for key, ids in parents.items()
        if len(ids) == 1 and len(territory.get(key, ())) == 1
    ]
