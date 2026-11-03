"""Marking the regions and cities of a user's visited places as visited."""

from adventures.models import Location
from worldtravel.models import City, Region
from worldtravel.services import mark_cities_visited, mark_regions_visited


def sync_visited_regions(user):
    """
    Mark every region and city that holds one of the user's visited locations as visited.

    Uses the region and city already stored on each location, so no geocoding happens.
    Returns the newly marked ones: ``{new_regions, regions: {id: name}, new_cities, cities}``.
    """
    region_ids, city_ids = set(), set()
    for location in Location.objects.filter(user=user).select_related('region', 'city'):
        if not location.is_visited_status():
            continue
        if location.region_id:
            region_ids.add(location.region_id)
        if location.city_id:
            city_ids.add(location.city_id)

    new_region_ids = mark_regions_visited(user.id, region_ids)
    new_city_ids = mark_cities_visited(user.id, city_ids)
    return {
        'new_regions': len(new_region_ids),
        'regions': dict(Region.objects.filter(id__in=new_region_ids).values_list('id', 'name')) if new_region_ids else {},
        'new_cities': len(new_city_ids),
        'cities': dict(City.objects.filter(id__in=new_city_ids).values_list('id', 'name')) if new_city_ids else {},
    }
