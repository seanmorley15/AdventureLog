from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import requests
from geopy.distance import geodesic
import logging
from ..geocoding import search_google, search_osm

logger = logging.getLogger(__name__)

class RecommendationsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    HEADERS = {'User-Agent': 'AdventureLog Server'}

    # Quality thresholds
    MIN_GOOGLE_RATING = 3.0  # Minimum rating to include
    MIN_GOOGLE_REVIEWS = 5   # Minimum number of reviews
    MAX_RESULTS = 50         # Maximum results to return

    def calculate_quality_score(self, place_data):
        """
        Calculate a quality score based on multiple factors.
        Higher score = better quality recommendation.
        """
        import math
        score = 0.0
        
        # Rating contribution (0-50 points)
        rating = place_data.get('rating')
        if rating is not None and rating > 0:
            score += (rating / 5.0) * 50
        
        # Review count contribution (0-30 points, logarithmic scale)
        review_count = place_data.get('review_count')
        if review_count is not None and review_count > 0:
            # Logarithmic scale: 10 reviews = ~10 pts, 100 = ~20 pts, 1000 = ~30 pts
            score += min(30, math.log10(review_count) * 10)
        
        # Distance penalty (0-20 points, closer is better)
        distance_km = place_data.get('distance_km')
        if distance_km is not None:
            if distance_km < 1:
                score += 20
            elif distance_km < 5:
                score += 15
            elif distance_km < 10:
                score += 10
            elif distance_km < 20:
                score += 5
        
        # Verified/business status bonus (0-10 points)
        if place_data.get('is_verified') or place_data.get('business_status') == 'OPERATIONAL':
            score += 10
        
        # Has photos bonus (0-5 points)
        photos = place_data.get('photos')
        if photos and len(photos) > 0:
            score += 5
        
        # Has opening hours bonus (0-5 points)
        opening_hours = place_data.get('opening_hours')
        if opening_hours and len(opening_hours) > 0:
            score += 5
        
        return round(score, 2)

    def parse_google_places(self, places, origin):
        """
        Parse Google Places API results into unified format.
        Enhanced with quality filtering and comprehensive data extraction.
        """
        locations = []
        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)

        for place in places:
            location = place.get('location', {})
            types = place.get('types', [])
            
            # Extract display name
            display_name = place.get("displayName", {})
            name = display_name.get("text") if isinstance(display_name, dict) else display_name

            # Extract coordinates
            lat = location.get('latitude')
            lon = location.get('longitude')

            if not name or not lat or not lon:
                continue

            # Extract rating information
            rating = place.get('rating')
            review_count = place.get('userRatingCount', 0)
            
            # Quality filter: Skip low-rated or unreviewed places
            if rating and rating < self.MIN_GOOGLE_RATING:
                continue
            if review_count < self.MIN_GOOGLE_REVIEWS:
                continue

            # Calculate distance
            distance_km = geodesic(origin, (lat, lon)).km

            # Extract address information
            formatted_address = place.get("formattedAddress") or place.get("shortFormattedAddress")
            
            # Extract business status
            business_status = place.get('businessStatus')
            is_operational = business_status == 'OPERATIONAL'
            
            # Extract opening hours
            opening_hours = place.get('regularOpeningHours', {})
            current_opening_hours = place.get('currentOpeningHours', {})
            is_open_now = current_opening_hours.get('openNow')
            
            # Extract photos and construct URLs
            photos = place.get('photos', [])
            photo_urls = []
            if photos and api_key:
                # Get first 5 photos and construct full URLs
                for photo in photos[:5]:
                    photo_name = photo.get('name', '')
                    if photo_name:
                        # Construct Google Places Photo API URL
                        # Format: https://places.googleapis.com/v1/{name}/media?key={key}&maxHeightPx=800&maxWidthPx=800
                        photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?key={api_key}&maxHeightPx=800&maxWidthPx=800"
                        photo_urls.append(photo_url)
            
            # Extract contact information
            phone_number = place.get('nationalPhoneNumber') or place.get('internationalPhoneNumber')
            website = place.get('websiteUri')
            google_maps_uri = place.get('googleMapsUri')
            
            # Extract price level
            price_level = place.get('priceLevel')
            
            # Extract editorial summary/description
            editorial_summary = place.get('editorialSummary', {})
            description = editorial_summary.get('text') if isinstance(editorial_summary, dict) else None
            
            # Filter out unwanted types (generic categories)
            filtered_types = [t for t in types if t not in ['point_of_interest', 'establishment']]
            
            # Build unified response
            place_data = {
                "id": f"google:{place.get('id')}",
                "external_id": place.get('id'),
                "source": "google",
                "name": name,
                "description": description,
                "latitude": lat,
                "longitude": lon,
                "address": formatted_address,
                "distance_km": round(distance_km, 2),
                "rating": rating,
                "review_count": review_count,
                "price_level": price_level,
                "types": filtered_types,
                "primary_type": filtered_types[0] if filtered_types else None,
                "business_status": business_status,
                "is_open_now": is_open_now,
                "opening_hours": opening_hours.get('weekdayDescriptions', []) if opening_hours else None,
                "phone_number": phone_number,
                "website": website,
                "google_maps_url": google_maps_uri,
                "photos": photo_urls,
                "is_verified": is_operational,
            }
            
            # Calculate quality score
            place_data['quality_score'] = self.calculate_quality_score(place_data)
            
            locations.append(place_data)

        return locations
    
    def parse_overpass_response(self, data, request, origin):
        """
        Parse Overpass API (OSM) results into unified format.
        Enhanced with quality filtering and comprehensive data extraction.
        """
        nodes = data.get('elements', [])
        locations = []

        for node in nodes:
            if node.get('type') not in ['node', 'way', 'relation']:
                continue

            tags = node.get('tags', {})
            
            # Get coordinates (for ways/relations, use center)
            lat = node.get('lat') or node.get('center', {}).get('lat')
            lon = node.get('lon') or node.get('center', {}).get('lon')
            
            # Extract name (with fallbacks)
            name = tags.get('name') or tags.get('official_name') or tags.get('alt_name')

            if not name or lat is None or lon is None:
                continue

            # Calculate distance
            distance_km = round(geodesic(origin, (lat, lon)).km, 2) if origin else None

            # Extract address information
            address_parts = [
                tags.get('addr:housenumber'),
                tags.get('addr:street'),
                tags.get('addr:suburb') or tags.get('addr:neighbourhood'),
                tags.get('addr:city'),
                tags.get('addr:state'),
                tags.get('addr:postcode'),
                tags.get('addr:country')
            ]
            formatted_address = ", ".join(filter(None, address_parts)) or None

            # Extract contact information
            phone = tags.get('phone') or tags.get('contact:phone')
            website = tags.get('website') or tags.get('contact:website') or tags.get('url')
            
            # Extract opening hours
            opening_hours = tags.get('opening_hours')
            
            # Extract rating/stars (if available)
            stars = tags.get('stars')
            
            # Determine category/type hierarchy
            category_keys = ['tourism', 'leisure', 'amenity', 'natural', 'historic', 'attraction', 'shop', 'sport']
            types = [tags.get(key) for key in category_keys if key in tags]
            primary_type = types[0] if types else None
            
            # Extract description and additional info
            description = tags.get('description') or tags.get('note')
            wikipedia = tags.get('wikipedia') or tags.get('wikidata')
            
            # Extract image if available
            image = tags.get('image') or tags.get('wikimedia_commons')
            
            # Quality filters for OSM data
            # Skip if it's just a generic POI without specific category
            if not primary_type:
                continue
            
            # Skip construction or disused places
            if tags.get('disused') or tags.get('construction'):
                continue
            
            # Build unified response
            place_data = {
                "id": f"osm:{node.get('type')}:{node.get('id')}",
                "external_id": str(node.get('id')),
                "source": "osm",
                "name": name,
                "description": description,
                "latitude": lat,
                "longitude": lon,
                "address": formatted_address,
                "distance_km": distance_km,
                "rating": None,  # OSM doesn't have ratings
                "review_count": None,
                "price_level": None,
                "types": types,
                "primary_type": primary_type,
                "business_status": None,
                "is_open_now": None,
                "opening_hours": [opening_hours] if opening_hours else None,
                "phone_number": phone,
                "website": website,
                "google_maps_url": None,
                "photos": [image] if image else [],
                "is_verified": bool(wikipedia),  # Has Wikipedia = more verified
                "osm_type": node.get('type'),
                "wikipedia": wikipedia,
                "stars": stars,
                "cuisine": tags.get('cuisine'),
                "wheelchair": tags.get('wheelchair'),
                "fee": tags.get('fee'),
            }
            
            # Calculate quality score (will be lower without ratings)
            place_data['quality_score'] = self.calculate_quality_score(place_data)
            
            locations.append(place_data)

        return locations

    
    def query_overpass(self, lat, lon, radius, category, request):
        """
        Query Overpass API (OpenStreetMap) for nearby places.
        Enhanced with better queries and error handling.
        """
        # Limit radius for OSM to prevent timeouts (max 5km for OSM due to server limits)
        osm_radius = min(radius, 5000)
        
        # Build optimized query - use simpler queries and limit results
        # Reduced timeout and simplified queries to prevent 504 errors
        if category == 'tourism':
            query = f"""
                [out:json][timeout:25];
                (
                  nwr["tourism"~"attraction|viewpoint|museum|gallery|zoo|aquarium"](around:{osm_radius},{lat},{lon});
                  nwr["historic"~"monument|castle|memorial"](around:{osm_radius},{lat},{lon});
                  nwr["leisure"~"park|garden|nature_reserve"](around:{osm_radius},{lat},{lon});
                );
                out center tags 50;
                """
        elif category == 'lodging':
            query = f"""
                [out:json][timeout:25];
                nwr["tourism"~"hotel|motel|guest_house|hostel"](around:{osm_radius},{lat},{lon});
                out center tags 50;
                """
        elif category == 'food':
            query = f"""
                [out:json][timeout:25];
                nwr["amenity"~"restaurant|cafe|bar|pub"](around:{osm_radius},{lat},{lon});
                out center tags 50;
                """
        else:
            logger.error(f"Invalid category requested: {category}")
            return {"error": "Invalid category.", "results": []}

        try:
            response = requests.post(
                self.OVERPASS_URL,
                data=query,
                headers=self.HEADERS,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            logger.warning(f"Overpass API timeout for {category} at ({lat}, {lon}) with radius {osm_radius}m")
            return {"error": f"OpenStreetMap query timed out. The service is overloaded. Radius limited to {int(osm_radius)}m.", "results": []}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 504:
                logger.warning(f"Overpass API 504 Gateway Timeout for {category}")
                return {"error": "OpenStreetMap server is overloaded. Try again later or use Google source.", "results": []}
            logger.warning(f"Overpass API HTTP error: {e}")
            return {"error": f"OpenStreetMap error: please try again later.", "results": []}
        except requests.exceptions.RequestException as e:
            logger.warning(f"Overpass API error: {e}")
            return {"error": f"OpenStreetMap temporarily unavailable: please try again later.", "results": []}
        except ValueError as e:
            logger.error(f"Invalid JSON response from Overpass: {e}")
            return {"error": "Invalid response from OpenStreetMap.", "results": []}

        origin = (float(lat), float(lon))
        locations = self.parse_overpass_response(data, request, origin)
        
        logger.info(f"Overpass returned {len(locations)} results")
        return {"error": None, "results": locations}

    def query_google_nearby(self, lat, lon, radius, category, request):
        """
        Query Google Places API (New) for nearby places.
        Enhanced with comprehensive field masks and better error handling.
        """
        api_key = settings.GOOGLE_MAPS_API_KEY
        
        url = "https://places.googleapis.com/v1/places:searchNearby"
        
        # Comprehensive field mask to get all useful information
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': (
                'places.id,'
                'places.displayName,'
                'places.formattedAddress,'
                'places.shortFormattedAddress,'
                'places.location,'
                'places.types,'
                'places.rating,'
                'places.userRatingCount,'
                'places.businessStatus,'
                'places.priceLevel,'
                'places.websiteUri,'
                'places.googleMapsUri,'
                'places.nationalPhoneNumber,'
                'places.internationalPhoneNumber,'
                'places.editorialSummary,'
                'places.photos,'
                'places.currentOpeningHours,'
                'places.regularOpeningHours'
            )
        }
        
        # Map categories to place types - use multiple types for better coverage
        type_mapping = {
            'lodging': ['lodging', 'hotel', 'hostel', 'resort_hotel', 'extended_stay_hotel'],
            'food': ['restaurant', 'cafe', 'bar', 'bakery', 'meal_takeaway', 'meal_delivery'],
            'tourism': ['tourist_attraction', 'museum', 'art_gallery', 'aquarium', 'zoo', 'amusement_park', 'park', 'natural_feature'],
        }
        
        payload = {
            "includedTypes": type_mapping.get(category, ['tourist_attraction']),
            "maxResultCount": 20,
            "rankPreference": "DISTANCE",  # Sort by distance first
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": float(lat),
                        "longitude": float(lon)
                    },
                    "radius": float(radius)
                }
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            places = data.get('places', [])
            origin = (float(lat), float(lon))
            locations = self.parse_google_places(places, origin)
            
            logger.info(f"Google Places returned {len(locations)} quality results for category '{category}'")
            
            return Response(self._prepare_final_results(locations))
            
        except requests.exceptions.Timeout:
            logger.warning("Google Places API timeout, falling back to OSM")
            return self.query_overpass(lat, lon, radius, category, request)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Google Places API error: {e}, falling back to OSM")
            return self.query_overpass(lat, lon, radius, category, request)
        except Exception as e:
            logger.error(f"Unexpected error with Google Places API: {e}")
            return self.query_overpass(lat, lon, radius, category, request)

    def _prepare_final_results(self, locations):
        """
        Prepare final results: sort by quality score and limit results.
        """
        # Sort by quality score (highest first)
        locations.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        
        # Limit to MAX_RESULTS
        locations = locations[:self.MAX_RESULTS]
        
        return locations
    
    def _deduplicate_results(self, google_results, osm_results):
        """
        Deduplicate results from both sources based on name and proximity.
        Prioritize Google results when duplicates are found.
        """
        from difflib import SequenceMatcher
        
        def is_similar(name1, name2, threshold=0.85):
            """Check if two names are similar using fuzzy matching."""
            return SequenceMatcher(None, name1.lower(), name2.lower()).ratio() > threshold
        
        def is_nearby(loc1, loc2, max_distance_m=50):
            """Check if two locations are within max_distance_m meters."""
            dist = geodesic(
                (loc1['latitude'], loc1['longitude']),
                (loc2['latitude'], loc2['longitude'])
            ).meters
            return dist < max_distance_m
        
        # Start with all Google results (higher quality)
        deduplicated = list(google_results)
        
        # Add OSM results that don't match Google results
        for osm_loc in osm_results:
            is_duplicate = False
            for google_loc in google_results:
                if (is_similar(osm_loc['name'], google_loc['name']) and 
                    is_nearby(osm_loc, google_loc)):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(osm_loc)
        
        return deduplicated

    @action(detail=False, methods=['get'])
    def query(self, request):
        """
        Query both Google Places and OSM for recommendations.
        Returns unified, high-quality results sorted by quality score.
        
        Query Parameters:
        - lat (required): Latitude
        - lon (required): Longitude  
        - radius (optional): Search radius in meters (default: 5000, max: 50000)
        - category (required): Category - 'tourism', 'food', or 'lodging'
        - sources (optional): Comma-separated sources - 'google', 'osm', or 'both' (default: 'both')
        """
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        # Allow a free-text `location` parameter which will be geocoded
        location_param = request.query_params.get('location')
        radius = request.query_params.get('radius', '5000')
        category = request.query_params.get('category')
        sources = request.query_params.get('sources', 'both').lower()

        # If lat/lon not supplied, try geocoding the free-text location param
        if (not lat or not lon) and location_param:
            geocode_results = None
            # Try Google first if API key configured
            if getattr(settings, 'GOOGLE_MAPS_API_KEY', None):
                try:
                    geocode_results = search_google(location_param)
                except Exception:
                    logger.warning("Google geocoding failed; falling back to OSM")
                    geocode_results = None

            # Fallback to OSM Nominatim
            if not geocode_results:
                try:
                    geocode_results = search_osm(location_param)
                except Exception:
                    logger.warning("OSM geocoding failed")
                    geocode_results = None

            # Validate geocode results
            if isinstance(geocode_results, dict) and geocode_results.get('error'):
                # Log internal geocoding error but avoid exposing sensitive details
                logger.warning("Geocoding helper returned an internal error")
                return Response({"error": "Geocoding failed. Please try a different location or contact support."}, status=400)

            if not geocode_results:
                return Response({"error": "Could not geocode provided location."}, status=400)

            # geocode_results expected to be a list of results; pick the best (first)
            best = None
            if isinstance(geocode_results, list) and len(geocode_results) > 0:
                best = geocode_results[0]
            elif isinstance(geocode_results, dict):
                # Some helpers might return a dict when only one result found
                best = geocode_results

            if not best:
                return Response({"error": "No geocoding results found."}, status=400)

            try:
                lat = float(best.get('lat') or best.get('latitude'))
                lon = float(best.get('lon') or best.get('longitude'))
            except Exception:
                return Response({"error": "Geocoding result missing coordinates."}, status=400)

            # Replace location_param with display name when available for logging/debug
            location_param = best.get('display_name') or best.get('name') or location_param

        # Validation: require lat and lon at this point
        if not lat or not lon:
            return Response({
                "error": "Latitude and longitude parameters are required (or provide a 'location' parameter to geocode)."
            }, status=400)
        
        try:
            lat = float(lat)
            lon = float(lon)
            radius = min(float(radius), 50000)  # Max 50km radius
        except ValueError:
            return Response({
                "error": "Invalid latitude, longitude, or radius value."
            }, status=400)

        valid_categories = ['lodging', 'food', 'tourism']
        if category not in valid_categories:
            return Response({
                "error": f"Invalid category. Valid categories: {', '.join(valid_categories)}"
            }, status=400)

        valid_sources = ['google', 'osm', 'both']
        if sources not in valid_sources:
            return Response({
                "error": f"Invalid sources. Valid options: {', '.join(valid_sources)}"
            }, status=400)

        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        
        google_results = []
        osm_results = []
        
        # Query Google Places if available and requested
        if api_key and sources in ['google', 'both']:
            try:
                url = "https://places.googleapis.com/v1/places:searchNearby"
                headers = {
                    'Content-Type': 'application/json',
                    'X-Goog-Api-Key': api_key,
                    'X-Goog-FieldMask': (
                        'places.id,places.displayName,places.formattedAddress,'
                        'places.shortFormattedAddress,places.location,places.types,'
                        'places.rating,places.userRatingCount,places.businessStatus,'
                        'places.priceLevel,places.websiteUri,places.googleMapsUri,'
                        'places.nationalPhoneNumber,places.internationalPhoneNumber,'
                        'places.editorialSummary,places.photos,'
                        'places.currentOpeningHours,places.regularOpeningHours'
                    )
                }
                
                type_mapping = {
                    'lodging': ['lodging', 'hotel', 'hostel', 'resort_hotel'],
                    'food': ['restaurant', 'cafe', 'bar', 'bakery'],
                    'tourism': ['tourist_attraction', 'museum', 'art_gallery', 'aquarium', 'zoo', 'park'],
                }
                
                payload = {
                    "includedTypes": type_mapping.get(category, ['tourist_attraction']),
                    "maxResultCount": 20,
                    "rankPreference": "DISTANCE",
                    "locationRestriction": {
                        "circle": {
                            "center": {"latitude": lat, "longitude": lon},
                            "radius": radius
                        }
                    }
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                places = data.get('places', [])
                origin = (lat, lon)
                google_results = self.parse_google_places(places, origin)
                logger.info(f"Google Places: {len(google_results)} quality results")
                
            except Exception as e:
                logger.warning(f"Google Places failed: {e}")
        
        # Query OSM if requested or as fallback
        osm_error = None
        if sources in ['osm', 'both'] or (sources == 'google' and not google_results):
            osm_response = self.query_overpass(lat, lon, radius, category, request)
            osm_results = osm_response.get('results', [])
            osm_error = osm_response.get('error')
            
            if osm_error:
                logger.warning(f"OSM query had issues: {osm_error}")
        
        # Combine and deduplicate if using both sources
        if sources == 'both' and google_results and osm_results:
            all_results = self._deduplicate_results(google_results, osm_results)
        else:
            all_results = google_results + osm_results
        
        # Prepare final results
        final_results = self._prepare_final_results(all_results)
        
        logger.info(f"Returning {len(final_results)} total recommendations")
        
        # Build response with metadata
        response_data = {
            "count": len(final_results),
            "results": final_results,
            "sources_used": {
                "google": len(google_results),
                "osm": len(osm_results),
                "total_before_dedup": len(google_results) + len(osm_results)
            }
        }
        
        # Add warnings if there were errors but we still have some results
        warnings = []
        if osm_error and len(osm_results) == 0:
            warnings.append(osm_error)
        
        if warnings:
            response_data["warnings"] = warnings
        
        # If no results at all and user requested only OSM, return error status
        if len(final_results) == 0 and sources == 'osm' and osm_error:
            # Log internal error notice for investigation but do not expose details to clients
            logger.debug("OSM query error (internal)")
            return Response({
                "error": "OpenStreetMap service temporarily unavailable. Please try again later.",
                "count": 0,
                "results": [],
                "sources_used": response_data["sources_used"]
            }, status=503)
        
        return Response(response_data)