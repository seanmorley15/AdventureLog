"""
What a user has visited, counting places the dataset lists twice.

Puerto Rico is a country and also a region of the United States. The two are read as one place,
and a visit counts once. Visits are made on the country, the territory, and the region under the
larger country mirrors them:

- a region that is also a country (``Region.territory``) is visited when any region of that
  country is, and
- it cannot be marked or unmarked itself, since the country's own pages are where that is done.

Only the rows the user made are stored. The rest is worked out here, so nothing can drift apart.
The cities of such a region are merged onto the country when the world data is imported.
"""

from django.db.models import Exists, OuterRef

from worldtravel.models import Region, VisitedRegion


def territory_of_region(region):
    """The country a region is also listed as, if any. Visits to it are made on that country's own pages."""
    return region.territory if region.territory_id else None


def umbrella_regions(user_id):
    """
    ``{region_id: country_pk}`` of the regions that count as visited only through their country.

    Regions the user has marked themselves are left out, since they already have a row.
    """
    visited_in_country = VisitedRegion.objects.filter(user_id=user_id, region__country_id=OuterRef('territory_id'))
    marked = VisitedRegion.objects.filter(user_id=user_id, region_id=OuterRef('id'))
    return dict(
        Region.objects.filter(territory__isnull=False)
        .filter(Exists(visited_in_country))
        .exclude(Exists(marked))
        .values_list('id', 'country_id')
    )


def country_behind_region(user_id, region_id):
    """
    The country that makes a region visited, or None.

    Such a region stays visited until the user unmarks the country's own regions.
    """
    region = Region.objects.filter(id=region_id, territory__isnull=False).select_related('territory').first()
    if region is None:
        return None
    visited = VisitedRegion.objects.filter(user_id=user_id, region__country_id=region.territory_id).exists()
    return region.territory if visited else None


def visited_totals(user_id):
    """
    ``(regions, countries)`` the user has visited, counting each place once.

    Puerto Rico is a country and a region of the United States. A visit there counts as the
    country, and the region under the United States is not counted on top of it.
    """
    rows = list(VisitedRegion.objects.filter(user_id=user_id).values_list('region__country_id', 'region__territory_id'))
    own_country_visited = {country_pk for country_pk, territory_pk in rows if territory_pk is None}
    # A row for the region under the larger country adds nothing once its country has a visit of its own.
    regions = sum(1 for _, territory_pk in rows if territory_pk is None or territory_pk not in own_country_visited)
    countries = {territory_pk or country_pk for country_pk, territory_pk in rows}
    return regions, len(countries)


def is_region_visited(user_id, region):
    if VisitedRegion.objects.filter(user_id=user_id, region=region).exists():
        return True
    if region.territory_id:
        return VisitedRegion.objects.filter(user_id=user_id, region__country_id=region.territory_id).exists()
    return False


def visited_region_ids(user_id):
    return set(VisitedRegion.objects.filter(user_id=user_id).values_list('region_id', flat=True)) | set(
        umbrella_regions(user_id)
    )
