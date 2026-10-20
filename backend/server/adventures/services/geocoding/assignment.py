"""Fill in a Location's country, region and city from its coordinates."""

import logging

from adventures.models import Location
from adventures.services.geocoding.reverse import reverse_geocode as reverse_geocode_service
from core.geo import has_coordinates, point_to_lat_lon
from worldtravel.models import City, Country, Region
from worldtravel.services import mark_cities_visited, mark_regions_visited

logger = logging.getLogger(__name__)


def geocode_and_assign_location(location_id: str):
    logger.debug("Starting geocode for location %s", location_id)
    try:
        location = Location.objects.get(id=location_id)
        if not has_coordinates(location.coordinates):
            return

        latitude, longitude = point_to_lat_lon(location.coordinates)
        is_visited = location.is_visited_status()
        selection = reverse_geocode_service(latitude, longitude, location.user)
        result = selection.data

        if 'region_id' in result:
            region = Region.objects.filter(id=result['region_id']).first()
            if region:
                location.region = region
                if is_visited:
                    mark_regions_visited(location.user_id, [region.id])

        if 'city_id' in result:
            city = City.objects.filter(id=result['city_id']).first()
            if city:
                location.city = city
                if is_visited:
                    mark_cities_visited(location.user_id, [city.id])

        if 'country_id' in result:
            country = Country.objects.filter(country_code=result['country_id']).first()
            if country:
                location.country = country

        # Save updated location info
        # Save updated location info, skip geocode threading
        location.save(update_fields=["region", "city", "country"], _skip_geocode=True)

    except Exception:
        logger.exception("Geocode failed for location %s", location_id)


def apply_reverse_geocode_result(location, reverse_data, fallback_location):
    """Fill in a place's region, city, country and address text from a reverse-geocode result."""
    if not isinstance(reverse_data, dict):
        reverse_data = {}

    updated_fields = []

    region_id = reverse_data.get('region_id')
    if region_id:
        region = Region.objects.filter(id=region_id).first()
        if region and location.region_id != region.id:
            location.region = region
            updated_fields.append('region')

    city_id = reverse_data.get('city_id')
    if city_id:
        city = City.objects.filter(id=city_id).first()
        if city and location.city_id != city.id:
            location.city = city
            updated_fields.append('city')

    country_id = reverse_data.get('country_id')
    if country_id:
        country = Country.objects.filter(country_code=country_id).first()
        if country and location.country_id != country.id:
            location.country = country
            updated_fields.append('country')

    if fallback_location and not location.location:
        location.location = fallback_location
        updated_fields.append('location')

    if updated_fields:
        location.save(update_fields=updated_fields, _skip_geocode=True)
