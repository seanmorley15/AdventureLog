import requests
import time
import socket
from worldtravel.models import Region, City, VisitedRegion, VisitedCity

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
        visited_region = VisitedRegion.objects.filter(region=region, user_id=user).first()
        
        region_visited = False
        city_visited = False
        country_code = iso_code[:2]
        
        if region:
            if town_city_or_county:
                display_name = f"{town_city_or_county}, {region.name}, {country_code}"
                city = City.objects.filter(name__contains=town_city_or_county, region=region).first()
                visited_city = VisitedCity.objects.filter(city=city, user_id=user).first()

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
        return False  # silently fail

def reverse_geocode(lat, lon, user):
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}"
    headers = {'User-Agent': 'AdventureLog Server'}
    connect_timeout = 1  # instead of 0.3
    read_timeout = 5     # instead of 2


    if not is_host_resolvable("nominatim.openstreetmap.org"):
        return {"error": "DNS resolution failed"}

    start = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=(connect_timeout, read_timeout))
        response.raise_for_status()
        data = response.json()
        elapsed = time.time() - start
        return extractIsoCode(user, data)

    except requests.exceptions.ConnectionError as e:
        return {"error": "Could not connect to geocoding service"}
    except requests.exceptions.Timeout as e:
        return {"error": "Geocoding service timed out"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error from geocoding service: {e}"}
    except requests.exceptions.JSONDecodeError as e:
        return {"error": "Invalid response from geocoding service"}
    except Exception as e:
        return {"error": f"Unexpected geocoding error: {str(e)}"}