import requests
import time
import socket
from worldtravel.models import Region, City, VisitedRegion, VisitedCity
from django.conf import settings

# -----------------
# SEARCHING
def search_google(query):
    try:
        api_key = settings.GOOGLE_MAPS_API_KEY
        if not api_key:
            return {"error": "Missing Google Maps API key"}

        # Updated to use the new Places API (New) endpoint
        url = "https://places.googleapis.com/v1/places:searchText"
        
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': 'places.displayName.text,places.formattedAddress,places.location,places.types,places.rating,places.userRatingCount'
        }
        
        payload = {
            "textQuery": query,
            "maxResultCount": 20  # Adjust as needed
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=(2, 5))
        response.raise_for_status()

        data = response.json()
        
        # Check if we have places in the response
        places = data.get("places", [])
        if not places:
            return {"error": "No results found"}

        results = []
        for place in places:
            location = place.get("location", {})
            types = place.get("types", [])
            primary_type = types[0] if types else None
            category = _extract_google_category(types)
            addresstype = _infer_addresstype(primary_type)

            importance = None
            rating = place.get("rating")
            ratings_total = place.get("userRatingCount")
            if rating is not None and ratings_total:
                importance = round(float(rating) * ratings_total / 100, 2)

            # Extract display name from the new API structure
            display_name_obj = place.get("displayName", {})
            name = display_name_obj.get("text") if display_name_obj else None

            results.append({
                "lat": location.get("latitude"),
                "lon": location.get("longitude"),
                "name": name,
                "display_name": place.get("formattedAddress"),
                "type": primary_type,
                "category": category,
                "importance": importance,
                "addresstype": addresstype,
                "powered_by": "google",
            })

        if results:
            results.sort(key=lambda r: r["importance"] if r["importance"] is not None else 0, reverse=True)

        return results

    except requests.exceptions.RequestException as e:
        return {"error": "Network error while contacting Google Maps", "details": str(e)}

    except Exception as e:
        return {"error": "Unexpected error during Google search", "details": str(e)}

def _extract_google_category(types):
    # Basic category inference based on common place types
    if not types:
        return None
    if "restaurant" in types:
        return "food"
    if "lodging" in types:
        return "accommodation"
    if "park" in types or "natural_feature" in types:
        return "nature"
    if "museum" in types or "tourist_attraction" in types:
        return "attraction"
    if "locality" in types or "administrative_area_level_1" in types:
        return "region"
    return types[0]  # fallback to first type


def _infer_addresstype(type_):
    # Rough mapping of Google place types to OSM-style addresstypes
    mapping = {
        "locality": "city",
        "sublocality": "neighborhood",
        "administrative_area_level_1": "region",
        "administrative_area_level_2": "county",
        "country": "country",
        "premise": "building",
        "point_of_interest": "poi",
        "route": "road",
        "street_address": "address",
    }
    return mapping.get(type_, None)


def search_osm(query):
    url = f"https://nominatim.openstreetmap.org/search?q={query}&format=jsonv2"
    headers = {'User-Agent': 'AdventureLog Server'}
    response = requests.get(url, headers=headers)
    data = response.json()

    return [{
        "lat": item.get("lat"),
        "lon": item.get("lon"),
        "name": item.get("name"),
        "display_name": item.get("display_name"),
        "type": item.get("type"),
        "category": item.get("category"),
        "importance": item.get("importance"),
        "addresstype": item.get("addresstype"),
        "powered_by": "nominatim",
    } for item in data]

# -----------------
# REVERSE GEOCODING
# -----------------

def extractIsoCode(user, data):
        """
        Extract the ISO code from the response data.
        Returns a dictionary containing the region name, country name, and ISO code if found.
        """
        iso_code = None
        town_city_or_county = None
        display_name = None
        country_code = None
        city = None
        visited_city = None
        location_name = None

        # town = None
        # city = None
        # county = None

        if 'name' in data.keys():
            location_name = data['name']
        
        if 'address' in data.keys():
            keys = data['address'].keys()
            for key in keys:
                if key.find("ISO") != -1:
                    iso_code = data['address'][key]
            if 'town' in keys:
                town_city_or_county = data['address']['town']
            if 'county' in keys:
                town_city_or_county = data['address']['county']
            if 'city' in keys:
                town_city_or_county = data['address']['city']
        if not iso_code:
            return {"error": "No region found"}
        
        region = Region.objects.filter(id=iso_code).first()
        visited_region = VisitedRegion.objects.filter(region=region, user=user).first()
        
        region_visited = False
        city_visited = False
        country_code = iso_code[:2]
        
        if region:
            if town_city_or_county:
                display_name = f"{town_city_or_county}, {region.name}, {country_code}"
                city = City.objects.filter(name__contains=town_city_or_county, region=region).first()
                visited_city = VisitedCity.objects.filter(city=city, user=user).first()

        if visited_region:
            region_visited = True
        if visited_city:
            city_visited = True
        if region:
            return {"region_id": iso_code, "region": region.name, "country": region.country.name, "country_id": region.country.country_code, "region_visited": region_visited, "display_name": display_name, "city": city.name if city else None, "city_id": city.id if city else None, "city_visited": city_visited, 'location_name': location_name}
        return {"error": "No region found"}

def is_host_resolvable(hostname: str) -> bool:
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.error:
        return False

def reverse_geocode(lat, lon, user):
    if getattr(settings, 'GOOGLE_MAPS_API_KEY', None):
        google_result = reverse_geocode_google(lat, lon, user)
        if "error" not in google_result:
            return google_result
        # If Google fails, fallback to OSM
        return reverse_geocode_osm(lat, lon, user)
    return reverse_geocode_osm(lat, lon, user)

def reverse_geocode_osm(lat, lon, user):
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}"
    headers = {'User-Agent': 'AdventureLog Server'}
    connect_timeout = 1
    read_timeout = 5

    if not is_host_resolvable("nominatim.openstreetmap.org"):
        return {"error": "DNS resolution failed"}

    try:
        response = requests.get(url, headers=headers, timeout=(connect_timeout, read_timeout))
        response.raise_for_status()
        data = response.json()
        return extractIsoCode(user, data)
    except Exception:
        return {"error": "An internal error occurred while processing the request"}

def reverse_geocode_google(lat, lon, user):
    api_key = settings.GOOGLE_MAPS_API_KEY
    
    # Updated to use the new Geocoding API endpoint (this one is still supported)
    # The Geocoding API is separate from Places API and still uses the old format
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"latlng": f"{lat},{lon}", "key": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            return {"error": "Geocoding failed"}

        # Convert Google schema to Nominatim-style for extractIsoCode
        first_result = data.get("results", [])[0]
        result_data = {
            "name": first_result.get("formatted_address"),
            "address": _parse_google_address_components(first_result.get("address_components", []))
        }
        return extractIsoCode(user, result_data)
    except Exception:
        return {"error": "An internal error occurred while processing the request"}

def _parse_google_address_components(components):
    parsed = {}
    country_code = None
    state_code = None

    for comp in components:
        types = comp.get("types", [])
        long_name = comp.get("long_name")
        short_name = comp.get("short_name")

        if "country" in types:
            parsed["country"] = long_name
            country_code = short_name
            parsed["ISO3166-1"] = short_name
        if "administrative_area_level_1" in types:
            parsed["state"] = long_name
            state_code = short_name
        if "administrative_area_level_2" in types:
            parsed["county"] = long_name
        if "locality" in types:
            parsed["city"] = long_name
        if "sublocality" in types:
            parsed["town"] = long_name

    # Build composite ISO 3166-2 code like US-ME
    if country_code and state_code:
        parsed["ISO3166-2-lvl1"] = f"{country_code}-{state_code}"

    return parsed