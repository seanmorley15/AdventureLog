"""The recommendation categories: one table that drives both Google and OpenStreetMap queries."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Category:
    key: str
    google_types: Tuple[str, ...]
    # (OSM tag, regex of accepted values). A value of ``.+`` accepts any value of the tag.
    osm_selectors: Tuple[Tuple[str, str], ...]
    is_lodging: bool = False


CATEGORIES: Dict[str, Category] = {
    c.key: c
    for c in (
        Category(
            'attractions',
            ('tourist_attraction', 'historical_landmark', 'monument', 'cultural_landmark', 'visitor_center'),
            (('tourism', 'attraction|viewpoint'), ('historic', 'monument|castle|memorial|ruins|archaeological_site|fort')),
        ),
        Category(
            'culture',
            ('museum', 'art_gallery', 'performing_arts_theater', 'cultural_center'),
            (('tourism', 'museum|gallery'), ('amenity', 'theatre|arts_centre')),
        ),
        Category(
            'nature',
            ('park', 'national_park', 'hiking_area', 'botanical_garden', 'beach'),
            (('leisure', 'park|garden|nature_reserve'), ('natural', 'beach|peak|waterfall')),
        ),
        Category(
            'food',
            ('restaurant', 'bakery', 'meal_takeaway'),
            (('amenity', 'restaurant|fast_food'), ('shop', 'bakery')),
        ),
        Category(
            'nightlife',
            ('cafe', 'coffee_shop', 'bar', 'pub', 'night_club'),
            (('amenity', 'cafe|bar|pub|nightclub'),),
        ),
        Category(
            'lodging',
            ('lodging', 'hotel', 'hostel', 'resort_hotel', 'bed_and_breakfast', 'campground'),
            (('tourism', 'hotel|motel|guest_house|hostel|camp_site'),),
            is_lodging=True,
        ),
        Category(
            'activities',
            ('amusement_park', 'zoo', 'aquarium', 'shopping_mall', 'market'),
            (('tourism', 'zoo|aquarium|theme_park'), ('leisure', 'water_park'), ('amenity', 'marketplace')),
        ),
    )
}

# Names older API clients still send.
ALIASES: Dict[str, str] = {'tourism': 'attractions'}

CATEGORY_CHOICES: List[str] = [*CATEGORIES.keys(), *ALIASES.keys()]


def get_category(key: str) -> Optional[Category]:
    return CATEGORIES.get(ALIASES.get(key, key))


def resolve_category_key(key: str) -> str:
    return ALIASES.get(key, key)
