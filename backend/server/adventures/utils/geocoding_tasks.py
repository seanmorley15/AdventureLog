"""
Consolidated background geocoding for Location, Transportation, and Lodging models.
"""

from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion


def background_geocode(model_class, obj_id: str):
    """
    Generic background geocode function that dispatches based on model type.

    Args:
        model_class: The Django model class (Location, Transportation, or Lodging)
        obj_id: UUID string of the object to geocode
    """
    model_name = model_class.__name__
    print(f"[{model_name} Geocode Thread] Starting geocode for {model_name.lower()} {obj_id}")
    try:
        obj = model_class.objects.get(id=obj_id)
        from adventures.geocoding import reverse_geocode

        if model_name == 'Transportation':
            _geocode_transportation(obj, reverse_geocode)
        elif model_name == 'Location':
            _geocode_location(obj, reverse_geocode)
        else:
            # Lodging (and any future model with lat/lon/country/region/city)
            _geocode_simple(obj, reverse_geocode)

    except Exception as e:
        print(f"[{model_name} Geocode Thread] Error processing {obj_id}: {e}")


def _geocode_location(location, reverse_geocode):
    """Geocode a Location, including visited region/city tracking."""
    if not (location.latitude and location.longitude):
        return

    is_visited = location.is_visited_status()
    result = reverse_geocode(location.latitude, location.longitude, location.user)

    if 'region_id' in result:
        region = Region.objects.filter(id=result['region_id']).first()
        if region:
            location.region = region
            if is_visited:
                VisitedRegion.objects.get_or_create(user=location.user, region=region)

    if 'city_id' in result:
        city = City.objects.filter(id=result['city_id']).first()
        if city:
            location.city = city
            if is_visited:
                VisitedCity.objects.get_or_create(user=location.user, city=city)

    if 'country_id' in result:
        country = Country.objects.filter(country_code=result['country_id']).first()
        if country:
            location.country = country

    location.save(update_fields=["region", "city", "country"], _skip_geocode=True)


def _geocode_simple(obj, reverse_geocode):
    """Geocode a model with latitude/longitude/country/region/city fields (e.g., Lodging)."""
    if not (obj.latitude and obj.longitude):
        return

    result = reverse_geocode(obj.latitude, obj.longitude, obj.user)

    if 'region_id' in result:
        region = Region.objects.filter(id=result['region_id']).first()
        if region:
            obj.region = region

    if 'city_id' in result:
        city = City.objects.filter(id=result['city_id']).first()
        if city:
            obj.city = city

    if 'country_id' in result:
        country = Country.objects.filter(country_code=result['country_id']).first()
        if country:
            obj.country = country

    # Update price_currency from country if still the default 'USD'
    update_fields = ["region", "city", "country"]
    if obj.country and str(obj.price_currency) == 'USD':
        currency_code = getattr(obj.country, 'currency_code', None)
        if currency_code and str(currency_code).strip():
            obj.price_currency = str(currency_code).strip()
            update_fields.append("price_currency")

    obj.save(update_fields=update_fields, _skip_geocode=True)


def _geocode_transportation(transportation, reverse_geocode):
    """Geocode a Transportation with origin and destination points."""
    # Geocode origin
    if transportation.origin_latitude and transportation.origin_longitude:
        result = reverse_geocode(transportation.origin_latitude, transportation.origin_longitude, transportation.user)
        if 'country_id' in result:
            country = Country.objects.filter(country_code=result['country_id']).first()
            if country:
                transportation.origin_country = country

    # Geocode destination
    if transportation.destination_latitude and transportation.destination_longitude:
        result = reverse_geocode(transportation.destination_latitude, transportation.destination_longitude, transportation.user)
        if 'country_id' in result:
            country = Country.objects.filter(country_code=result['country_id']).first()
            if country:
                transportation.destination_country = country

    # Update price_currency from origin country if still the default 'USD'
    update_fields = ["origin_country", "destination_country"]
    if transportation.origin_country and str(transportation.price_currency) == 'USD':
        currency_code = getattr(transportation.origin_country, 'currency_code', None)
        if currency_code and str(currency_code).strip():
            transportation.price_currency = str(currency_code).strip()
            update_fields.append("price_currency")

    transportation.save(update_fields=update_fields, _skip_geocode=True)
