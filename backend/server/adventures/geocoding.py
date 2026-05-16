import requests
import time
import socket
import re
import unicodedata
from urllib.parse import quote
from worldtravel.models import Region, City, VisitedRegion, VisitedCity
from django.conf import settings

# -----------------
# SEARCHING
def search_google(query):
    try:
        api_key = settings.GOOGLE_MAPS_API_KEY
        if not api_key:
            return {"error": "Geocoding service unavailable. Please check configuration."}

        # Updated to use the new Places API (New) endpoint
        url = "https://places.googleapis.com/v1/places:searchText"
        
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': (
                'places.id,places.displayName.text,places.formattedAddress,places.location,'
                'places.types,places.rating,places.userRatingCount,places.websiteUri,'
                'places.nationalPhoneNumber,places.internationalPhoneNumber,'
                'places.editorialSummary.text,places.googleMapsUri,places.photos.name'
            )
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
            return {"error": "No locations found for the given query."}

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

            photos = []
            for photo in place.get('photos', [])[:5]:
                photo_name = photo.get('name')
                if photo_name:
                    photos.append(
                        f"https://places.googleapis.com/v1/{photo_name}/media?key={api_key}&maxHeightPx=800&maxWidthPx=800"
                    )

            # Extract display name from the new API structure
            display_name_obj = place.get("displayName", {})
            name = display_name_obj.get("text") if display_name_obj else None

            results.append({
                "lat": location.get("latitude"),
                "lon": location.get("longitude"),
                "name": name,
                "display_name": place.get("formattedAddress"),
                "place_id": place.get("id"),
                "type": primary_type,
                "types": types,
                "category": category,
                "description": (place.get('editorialSummary') or {}).get('text'),
                "website": place.get('websiteUri'),
                "phone_number": place.get('internationalPhoneNumber') or place.get('nationalPhoneNumber'),
                "google_maps_url": place.get('googleMapsUri'),
                "importance": importance,
                "rating": rating,
                "review_count": ratings_total,
                "photos": photos,
                "addresstype": addresstype,
                "powered_by": "google",
            })

        if results:
            results.sort(key=lambda r: r["importance"] if r["importance"] is not None else 0, reverse=True)

        return results

    except requests.exceptions.Timeout:
        return {"error": "Request timed out while contacting Google Maps. Please try again."}
    except requests.exceptions.ConnectionError:
        return {"error": "Unable to connect to Google Maps service. Please check your internet connection."}
    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            return {"error": "Invalid request to Google Maps. Please check your query."}
        elif response.status_code == 401:
            return {"error": "Authentication failed with Google Maps. Please check API configuration."}
        elif response.status_code == 403:
            return {"error": "Access forbidden to Google Maps. Please check API permissions."}
        elif response.status_code == 429:
            return {"error": "Too many requests to Google Maps. Please try again later."}
        else:
            return {"error": "Google Maps service error. Please try again later."}
    except requests.exceptions.RequestException:
        return {"error": "Network error while contacting Google Maps. Please try again."}
    except Exception:
        return {"error": "An unexpected error occurred during Google search. Please try again."}

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
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=jsonv2"
        headers = {'User-Agent': 'AdventureLog Server'}
        response = requests.get(url, headers=headers, timeout=(2, 5))
        response.raise_for_status()
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
    except requests.exceptions.Timeout:
        return {"error": "Request timed out while contacting OpenStreetMap. Please try again."}
    except requests.exceptions.ConnectionError:
        return {"error": "Unable to connect to OpenStreetMap service. Please check your internet connection."}
    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            return {"error": "Invalid request to OpenStreetMap. Please check your query."}
        elif response.status_code == 429:
            return {"error": "Too many requests to OpenStreetMap. Please try again later."}
        else:
            return {"error": "OpenStreetMap service error. Please try again later."}
    except requests.exceptions.RequestException:
        return {"error": "Network error while contacting OpenStreetMap. Please try again."}
    except Exception:
        return {"error": "An unexpected error occurred during OpenStreetMap search. Please try again."}

def search(query):
    """
    Unified search function that tries Google Maps first, then falls back to OpenStreetMap.
    """
    if getattr(settings, 'GOOGLE_MAPS_API_KEY', None):
        google_result = search_google(query)
        if "error" not in google_result:
            return google_result
        # If Google fails, fallback to OSM
    return search_osm(query)


def _fetch_wikipedia_summary(query, language='en'):
    normalized_query = (query or '').strip()
    if not normalized_query:
        return None

    candidates = [normalized_query]
    if ',' in normalized_query:
        head = normalized_query.split(',')[0].strip()
        if head and head not in candidates:
            candidates.append(head)

    for candidate in candidates:
        try:
            encoded_query = quote(candidate, safe='')
            url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{encoded_query}"
            response = requests.get(
                url,
                headers={'User-Agent': 'AdventureLog Server'},
                timeout=(2, 5),
            )
            if response.status_code != 200:
                continue

            data = response.json()
            if data.get('type') == 'disambiguation':
                continue

            extract = (data.get('extract') or '').strip()
            if len(extract) >= 120:
                return extract
        except requests.exceptions.RequestException:
            continue

    return None


def _compose_place_description(
    editorial_summary,
    review_snippets,
):
    parts = []

    summary = (editorial_summary or '').strip()
    if summary:
        parts.append(f"### About\n\n{summary}")

    cleaned_reviews = []
    for snippet in review_snippets:
        text = (snippet or '').strip()
        if len(text) >= 40:
            cleaned_reviews.append(text)
        if len(cleaned_reviews) >= 2:
            break

    if cleaned_reviews:
        review_block = '### Visitor Highlights\n\n' + '\n'.join(
            f"- {text}" for text in cleaned_reviews
        )
        parts.append(review_block)

    return '\n\n'.join(parts).strip() or None


def get_place_details(place_id, fallback_query=None, language='en'):
    if not place_id:
        return {'error': 'place_id is required'}

    details = {
        'description': None,
        'name': None,
        'formatted_address': None,
        'types': [],
        'rating': None,
        'review_count': None,
        'website': None,
        'phone_number': None,
        'google_maps_url': None,
        'source': None,
    }

    api_key = settings.GOOGLE_MAPS_API_KEY
    if api_key:
        try:
            url = f"https://places.googleapis.com/v1/places/{place_id}"
            headers = {
                'X-Goog-Api-Key': api_key,
                'X-Goog-FieldMask': (
                    'id,displayName.text,formattedAddress,editorialSummary.text,types,'
                    'rating,userRatingCount,websiteUri,nationalPhoneNumber,'
                    'internationalPhoneNumber,googleMapsUri,reviews.text.text'
                ),
            }
            response = requests.get(url, headers=headers, timeout=(2, 6))
            response.raise_for_status()

            place = response.json()
            details['name'] = (place.get('displayName') or {}).get('text')
            details['formatted_address'] = place.get('formattedAddress')
            details['types'] = place.get('types') or []
            details['rating'] = place.get('rating')
            details['review_count'] = place.get('userRatingCount')
            details['website'] = place.get('websiteUri')
            details['phone_number'] = (
                place.get('internationalPhoneNumber') or place.get('nationalPhoneNumber')
            )
            details['google_maps_url'] = place.get('googleMapsUri')

            editorial_summary = (place.get('editorialSummary') or {}).get('text')
            reviews = place.get('reviews') or []
            review_snippets = [((review.get('text') or {}).get('text')) for review in reviews]
            details['description'] = _compose_place_description(
                editorial_summary,
                review_snippets,
            )
            if details['description']:
                details['source'] = 'google'
        except requests.exceptions.RequestException:
            pass

    # Google summaries are often short; fallback to Wikipedia for richer context.
    description_text = (details.get('description') or '').strip()
    if len(description_text) < 220:
        wikipedia_summary = _fetch_wikipedia_summary(
            fallback_query or details.get('name') or '',
            language=language,
        )
        if wikipedia_summary:
            if description_text:
                details['description'] = f"{description_text}\n\n### Background\n\n{wikipedia_summary}"
                details['source'] = 'google+wikipedia'
            else:
                details['description'] = f"### Background\n\n{wikipedia_summary}"
                details['source'] = 'wikipedia'

    if not details.get('description'):
        return {'error': 'Unable to enrich place description'}

    return details


def _clean_location_candidate(value):
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _looks_like_street_address(value):
    candidate = _clean_location_candidate(value)
    if not candidate:
        return False

    lowered = candidate.lower()
    if not re.search(r"\d", lowered):
        return False

    if lowered.count(",") >= 2:
        return True

    if not re.match(r"^\d{1,6}\s+\S+", lowered):
        return False

    street_tokens = (
        "st",
        "street",
        "rd",
        "road",
        "ave",
        "avenue",
        "blvd",
        "boulevard",
        "dr",
        "drive",
        "ln",
        "lane",
        "ct",
        "court",
        "pl",
        "place",
        "pkwy",
        "parkway",
        "hwy",
        "highway",
        "trl",
        "trail",
    )
    return any(re.search(rf"\b{token}\b", lowered) for token in street_tokens)


def _first_preferred_location_name(candidates, allow_address_fallback=False):
    address_fallback = None
    for candidate in candidates:
        cleaned = _clean_location_candidate(candidate)
        if not cleaned:
            continue
        if not _looks_like_street_address(cleaned):
            return cleaned
        if address_fallback is None:
            address_fallback = cleaned
    return address_fallback if allow_address_fallback else None


def _extract_google_component_name(address_components):
    preferred_types = (
        "premise",
        "point_of_interest",
        "establishment",
        "subpremise",
        "natural_feature",
        "airport",
        "park",
        "tourist_attraction",
        "shopping_mall",
        "university",
        "school",
        "hospital",
    )

    for preferred_type in preferred_types:
        for component in address_components or []:
            types = component.get("types", [])
            if preferred_type in types:
                return component.get("long_name") or component.get("short_name")
    return None


def _score_google_result_types(types):
    priority = (
        "point_of_interest",
        "establishment",
        "premise",
        "subpremise",
        "tourist_attraction",
        "park",
        "airport",
        "shopping_mall",
        "university",
        "school",
        "hospital",
        "street_address",
        "route",
    )
    for idx, type_name in enumerate(priority):
        if type_name in types:
            return len(priority) - idx
    return 0


def _fetch_google_nearby_place_name(lat, lon, api_key):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'places.displayName.text,places.formattedAddress,places.types',
    }
    payload = {
        "maxResultCount": 6,
        "rankPreference": "DISTANCE",
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(lat),
                    "longitude": float(lon),
                },
                "radius": 45.0,
            }
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=(2, 5))
        response.raise_for_status()
        places = (response.json() or {}).get("places", [])
    except requests.exceptions.RequestException:
        return None

    candidates = [((place.get("displayName") or {}).get("text")) for place in places]
    return _first_preferred_location_name(candidates, allow_address_fallback=False)


def _extract_google_location_name(results, nearby_place_name=None):
    preferred_nearby = _first_preferred_location_name([nearby_place_name], allow_address_fallback=False)
    if preferred_nearby:
        return preferred_nearby

    scored_candidates = []
    for result in results or []:
        score = _score_google_result_types(result.get("types", []))
        if score <= 0:
            continue
        component_name = _extract_google_component_name(result.get("address_components", []))
        name_candidate = _first_preferred_location_name([component_name], allow_address_fallback=False)
        if name_candidate:
            scored_candidates.append((score, name_candidate))

    if scored_candidates:
        scored_candidates.sort(key=lambda item: item[0], reverse=True)
        return scored_candidates[0][1]

    component_candidates = [
        _extract_google_component_name(result.get("address_components", []))
        for result in (results or [])
    ]
    component_pick = _first_preferred_location_name(component_candidates, allow_address_fallback=False)
    if component_pick:
        return component_pick

    formatted_candidates = [result.get("formatted_address") for result in (results or [])]
    return _first_preferred_location_name(formatted_candidates, allow_address_fallback=True)


def _extract_osm_location_name(data):
    address = data.get("address", {}) or {}
    namedetails = data.get("namedetails", {}) or {}
    extratags = data.get("extratags", {}) or {}

    candidates = [
        data.get("name"),
        namedetails.get("name"),
        namedetails.get("official_name"),
        namedetails.get("short_name"),
        namedetails.get("brand"),
        namedetails.get("loc_name"),
        address.get("amenity"),
        address.get("tourism"),
        address.get("attraction"),
        address.get("building"),
        address.get("shop"),
        address.get("leisure"),
        address.get("historic"),
        address.get("man_made"),
        address.get("office"),
        address.get("aeroway"),
        address.get("railway"),
        address.get("public_transport"),
        address.get("craft"),
        address.get("house_name"),
        extratags.get("name"),
        extratags.get("official_name"),
        extratags.get("brand"),
        extratags.get("operator"),
    ]

    preferred = _first_preferred_location_name(candidates, allow_address_fallback=False)
    if preferred:
        return preferred

    return _first_preferred_location_name(
        [data.get("name"), data.get("display_name")],
        allow_address_fallback=True,
    )

# -----------------
# REVERSE GEOCODING
# -----------------

def extractIsoCode(user, data):
    """
    Extract the ISO code from the response data.
    Returns a dictionary containing the region name, country name, and ISO code if found.
    """
    iso_code = None
    display_name = None
    country_code = None
    city = None
    visited_city = None
    location_name = _clean_location_candidate(data.get('location_name') or data.get('name'))

    address = data.get('address', {}) or {}

    # Capture country code early for ISO selection and name fallback.
    country_code = address.get("ISO3166-1")
    state_name = address.get("state")

    # Prefer the most specific ISO 3166-2 code available before falling back to country-level.
    # France gets lvl4 (regions) first for city matching, then lvl6 (departments) as a fallback.
    preferred_iso_keys = (
        [
            "ISO3166-2-lvl10",
            "ISO3166-2-lvl9",
            "ISO3166-2-lvl8",
            "ISO3166-2-lvl4",
            "ISO3166-2-lvl6",
            "ISO3166-2-lvl7",
            "ISO3166-2-lvl5",
            "ISO3166-2-lvl3",
            "ISO3166-2-lvl2",
            "ISO3166-2-lvl1",
            "ISO3166-2",
        ]
        if country_code == "FR"
        else [
            "ISO3166-2-lvl10",
            "ISO3166-2-lvl9",
            "ISO3166-2-lvl8",
            "ISO3166-2-lvl4",
            "ISO3166-2-lvl7",
            "ISO3166-2-lvl6",
            "ISO3166-2-lvl5",
            "ISO3166-2-lvl3",
            "ISO3166-2-lvl2",
            "ISO3166-2-lvl1",
            "ISO3166-2",
        ]
    )

    iso_candidates = []
    for key in preferred_iso_keys:
        value = address.get(key)
        if value and value not in iso_candidates:
            iso_candidates.append(value)

    # If no region-level code, fall back to country code only as a last resort.
    if not iso_candidates and "ISO3166-1" in address:
        iso_candidates.append(address.get("ISO3166-1"))

    iso_code = iso_candidates[0] if iso_candidates else None

    region_candidates = []
    for candidate in iso_candidates:
        if len(str(candidate)) <= 2:
            continue
        match = Region.objects.filter(id=candidate).first()
        if match and match not in region_candidates:
            region_candidates.append(match)

    region = region_candidates[0] if region_candidates else None

    # Fallback: attempt to resolve region by name and country code when no ISO match.
    if not region and state_name:
        region_queryset = Region.objects.filter(name__iexact=state_name)
        if country_code:
            region_queryset = region_queryset.filter(country__country_code=country_code)
        region = region_queryset.first()
        if region:
            iso_code = region.id
            if not country_code:
                country_code = region.country.country_code
            if region not in region_candidates:
                region_candidates.insert(0, region)

    if not region:
        return {"error": "No region found"}

    if not country_code:
        country_code = region.country.country_code

    region_visited = False
    city_visited = False

    # ordered preference for best-effort locality matching
    locality_keys = [
        'suburb',
        'neighbourhood',
        'neighborhood',  # alternate spelling
        'city',
        'city_district',
        'town',
        'village',
        'hamlet',
        'locality',
        'municipality',
        'county',
    ]

    def _normalize_name(value):
        normalized = unicodedata.normalize("NFKD", value)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]", "", ascii_only.lower())

    def match_locality(key_name, target_region):
        value = address.get(key_name)
        if not value:
            return None
        qs = City.objects.filter(region=target_region)

        # Use exact matches first to avoid broad county/name collisions (e.g. Troms vs Tromsø).
        exact_match = qs.filter(name__iexact=value).first()
        if exact_match:
            return exact_match

        normalized_value = _normalize_name(value)
        for candidate in qs.values_list('id', 'name'):
            candidate_id, candidate_name = candidate
            if _normalize_name(candidate_name) == normalized_value:
                return qs.filter(id=candidate_id).first()

        # Allow partial matching for most locality fields but keep county strict.
        if key_name == 'county':
            return None

        return qs.filter(name__icontains=value).first()

    chosen_region = region
    for candidate_region in region_candidates or [region]:
        for key_name in locality_keys:
            city = match_locality(key_name, candidate_region)
            if city:
                chosen_region = candidate_region
                iso_code = chosen_region.id
                break
        if city:
            break

    region = chosen_region
    iso_code = region.id
    visited_region = VisitedRegion.objects.filter(region=region, user=user).first()
    region_visited = bool(visited_region)

    if city:
        display_name = f"{city.name}, {region.name}, {country_code or region.country.country_code}"
        visited_city = VisitedCity.objects.filter(city=city, user=user).first()
        city_visited = bool(visited_city)
    else:
        display_name = f"{region.name}, {country_code or region.country.country_code}"

    return {
        "region_id": iso_code,
        "region": region.name,
        "country": region.country.name,
        "country_id": region.country.country_code,
        "region_visited": region_visited,
        "display_name": display_name,
        "city": city.name if city else None,
        "city_id": city.id if city else None,
        "city_visited": city_visited,
        'location_name': location_name,
    }

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
    url = (
        "https://nominatim.openstreetmap.org/reverse"
        f"?format=jsonv2&addressdetails=1&namedetails=1&extratags=1&zoom=18&lat={lat}&lon={lon}"
    )
    headers = {'User-Agent': 'AdventureLog Server'}
    connect_timeout = 1
    read_timeout = 5

    if not is_host_resolvable("nominatim.openstreetmap.org"):
        return {"error": "Unable to resolve OpenStreetMap service. Please check your internet connection."}

    try:
        response = requests.get(url, headers=headers, timeout=(connect_timeout, read_timeout))
        response.raise_for_status()
        data = response.json()
        data["location_name"] = _extract_osm_location_name(data)
        return extractIsoCode(user, data)
    except requests.exceptions.Timeout:
        return {"error": "Request timed out while contacting OpenStreetMap. Please try again."}
    except requests.exceptions.ConnectionError:
        return {"error": "Unable to connect to OpenStreetMap service. Please check your internet connection."}
    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            return {"error": "Invalid request to OpenStreetMap. Please check coordinates."}
        elif response.status_code == 429:
            return {"error": "Too many requests to OpenStreetMap. Please try again later."}
        else:
            return {"error": "OpenStreetMap service error. Please try again later."}
    except requests.exceptions.RequestException:
        return {"error": "Network error while contacting OpenStreetMap. Please try again."}
    except Exception:
        return {"error": "An unexpected error occurred during OpenStreetMap geocoding. Please try again."}

def reverse_geocode_google(lat, lon, user):
    api_key = settings.GOOGLE_MAPS_API_KEY
    
    # Updated to use the new Geocoding API endpoint (this one is still supported)
    # The Geocoding API is separate from Places API and still uses the old format
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"latlng": f"{lat},{lon}", "key": api_key}

    try:
        response = requests.get(url, params=params, timeout=(2, 5))
        response.raise_for_status()
        data = response.json()

        status = data.get("status")
        if status != "OK":
            if status == "ZERO_RESULTS":
                return {"error": "No location found for the given coordinates."}
            elif status == "OVER_QUERY_LIMIT":
                return {"error": "Query limit exceeded for Google Maps. Please try again later."}
            elif status == "REQUEST_DENIED":
                return {"error": "Request denied by Google Maps. Please check API configuration."}
            elif status == "INVALID_REQUEST":
                return {"error": "Invalid request to Google Maps. Please check coordinates."}
            else:
                return {"error": "Geocoding failed. Please try again."}

        results = data.get("results", [])
        if not results:
            return {"error": "No location found for the given coordinates."}

        nearby_place_name = _fetch_google_nearby_place_name(lat, lon, api_key)
        location_name = _extract_google_location_name(results, nearby_place_name=nearby_place_name)

        # Convert Google schema to Nominatim-style for extractIsoCode
        first_result = results[0]
        address_result = next(
            (result for result in results if "plus_code" not in result.get("types", [])),
            first_result,
        )
        result_data = {
            "name": first_result.get("formatted_address"),
            "location_name": location_name,
            "address": _parse_google_address_components(address_result.get("address_components", [])),
        }
        return extractIsoCode(user, result_data)
    except requests.exceptions.Timeout:
        return {"error": "Request timed out while contacting Google Maps. Please try again."}
    except requests.exceptions.ConnectionError:
        return {"error": "Unable to connect to Google Maps service. Please check your internet connection."}
    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            return {"error": "Invalid request to Google Maps. Please check coordinates."}
        elif response.status_code == 401:
            return {"error": "Authentication failed with Google Maps. Please check API configuration."}
        elif response.status_code == 403:
            return {"error": "Access forbidden to Google Maps. Please check API permissions."}
        elif response.status_code == 429:
            return {"error": "Too many requests to Google Maps. Please try again later."}
        else:
            return {"error": "Google Maps service error. Please try again later."}
    except requests.exceptions.RequestException:
        return {"error": "Network error while contacting Google Maps. Please try again."}
    except Exception:
        return {"error": "An unexpected error occurred during Google geocoding. Please try again."}

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
        if "administrative_area_level_3" in types:
            parsed["municipality"] = long_name
        if "locality" in types:
            parsed["city"] = long_name
        if "postal_town" in types:
            parsed.setdefault("city", long_name)
        if "sublocality" in types or any(t.startswith("sublocality_level_") for t in types):
            parsed["suburb"] = long_name
        if "neighborhood" in types:
            parsed["neighbourhood"] = long_name
        if "route" in types:
            parsed["road"] = long_name
        if "street_address" in types:
            parsed["address"] = long_name

    # Build composite ISO 3166-2 code like US-ME (matches Region.id in DB)
    if country_code and state_code:
        parsed["ISO3166-2-lvl1"] = f"{country_code}-{state_code}"

    return parsed
