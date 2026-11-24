"""Turning provider geocoding payloads into display names. Pure: no database, no network."""

import re


def clean_location_candidate(value):
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


# Words that mark a street, as they are written where places are most often added.
_STREET_WORDS = frozenset({
    # English
    'st', 'street', 'rd', 'road', 'ave', 'avenue', 'blvd', 'boulevard', 'dr', 'drive', 'ln', 'lane',
    'ct', 'court', 'pl', 'place', 'pkwy', 'parkway', 'hwy', 'highway', 'trl', 'trail', 'terrace',
    # Romance languages
    'rue', 'chemin', 'impasse', 'allée', 'bd', 'calle', 'avenida', 'paseo', 'plaza', 'carrer',
    'avinguda', 'rua', 'travessa', 'via', 'viale', 'corso', 'piazza', 'strada',
    # German, Dutch, Nordic, Slavic
    'strasse', 'straße', 'str', 'gasse', 'weg', 'platz', 'allee', 'plein', 'laan', 'straat',
    'ulica', 'ul', 'ulice',
})
# Streets written as one word, in German, Dutch and the Nordic languages: Hauptstraße, Kerkstraat.
_STREET_SUFFIXES = ('straße', 'strasse', 'gasse', 'weg', 'platz', 'allee', 'laan', 'straat', 'gatan', 'vägen', 'gade', 'vej', 'veien')
# The street word comes first in these languages, with the house number after it.
_LEADING_STREET_WORDS = frozenset({
    'rue', 'chemin', 'impasse', 'calle', 'avenida', 'paseo', 'plaza', 'carrer', 'avinguda', 'rua',
    'travessa', 'via', 'viale', 'corso', 'piazza', 'strada', 'ulica', 'ul', 'ulice',
})
_HOUSE_NUMBER_THEN_BREAK = re.compile(r"\b\d{1,5}[a-z]?(?:\s*[-–/]\s*\d{1,5}[a-z]?)?\s*(?:,|$)")


def _is_street_word(word):
    word = word.strip('.,;:()')
    return word in _STREET_WORDS or word.endswith(_STREET_SUFFIXES)


def looks_like_street_address(value):
    """
    Whether text is a street address rather than the name of a place.

    A number then a street word ("12 Rue de Rivoli"), a street then its number ("Hauptstraße 5",
    "Via Roma 12"), or three or more comma-separated parts. Names that merely contain a number
    or a street word ("Route 66 Diner", "Café 21", "Strandweg Beach Bar") are not addresses.
    """
    candidate = clean_location_candidate(value)
    if not candidate:
        return False

    lowered = candidate.lower()
    if not re.search(r"\d", lowered):
        return False

    if lowered.count(",") >= 2:
        return True

    words = lowered.split()
    if re.match(r"^\d{1,6}[a-z]?\s+\S+", lowered):
        return any(_is_street_word(word) for word in words[1:])

    first = words[0].strip('.,;:()')
    if first in _LEADING_STREET_WORDS or first.endswith(_STREET_SUFFIXES):
        return bool(_HOUSE_NUMBER_THEN_BREAK.search(lowered))
    return False


def first_preferred_location_name(candidates, allow_address_fallback=False):
    address_fallback = None
    for candidate in candidates:
        cleaned = clean_location_candidate(candidate)
        if not cleaned:
            continue
        if not looks_like_street_address(cleaned):
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


def extract_osm_location_name(data):
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

    preferred = first_preferred_location_name(candidates, allow_address_fallback=False)
    if preferred:
        return preferred

    return first_preferred_location_name(
        [data.get("name"), data.get("display_name")],
        allow_address_fallback=True,
    )


def parse_google_address_components(components):
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

    if country_code and state_code:
        parsed["ISO3166-2-lvl1"] = f"{country_code}-{state_code}"

    return parsed


def extract_google_location_name(results, nearby_place_name=None):
    preferred_nearby = first_preferred_location_name([nearby_place_name], allow_address_fallback=False)
    if preferred_nearby:
        return preferred_nearby

    scored_candidates = []
    for result in results or []:
        score = _score_google_result_types(result.get("types", []))
        if score <= 0:
            continue
        component_name = _extract_google_component_name(result.get("address_components", []))
        name_candidate = first_preferred_location_name([component_name], allow_address_fallback=False)
        if name_candidate:
            scored_candidates.append((score, name_candidate))

    if scored_candidates:
        scored_candidates.sort(key=lambda item: item[0], reverse=True)
        return scored_candidates[0][1]

    component_candidates = [
        _extract_google_component_name(result.get("address_components", []))
        for result in (results or [])
    ]
    component_pick = first_preferred_location_name(component_candidates, allow_address_fallback=False)
    if component_pick:
        return component_pick

    formatted_candidates = [result.get("formatted_address") for result in (results or [])]
    return first_preferred_location_name(formatted_candidates, allow_address_fallback=True)
