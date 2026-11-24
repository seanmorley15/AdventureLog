"""Mapping the sport names other apps and file formats use onto ``SPORT_TYPE_CHOICES``."""

from __future__ import annotations

import re

from adventures.utils.sports_types import SPORT_CATEGORIES, SPORT_TYPE_CHOICES

DEFAULT_SPORT = 'General'
_VALID = {key for key, _label in SPORT_TYPE_CHOICES}

# Keyed by the lowercase name with spaces, dashes and underscores removed. Covers Strava,
# FIT (sport and sub_sport), TCX, GPX ``<type>`` values and Endurain.
_ALIASES = {
    'running': 'Run', 'run': 'Run', 'street': 'Run', 'treadmill': 'Run', 'track': 'Run',
    'trailrunning': 'TrailRun', 'trail': 'TrailRun', 'trailrun': 'TrailRun',
    'virtualrun': 'VirtualRun', 'virtualrunning': 'VirtualRun',
    'walking': 'Walk', 'walk': 'Walk', 'speedwalking': 'Walk',
    'hiking': 'Hike', 'hike': 'Hike',
    'biking': 'Ride', 'cycling': 'Ride', 'ride': 'Ride', 'road': 'Ride', 'roadbike': 'Ride',
    'spin': 'Ride', 'indoorcycling': 'Ride',
    'mountainbiking': 'MountainBikeRide', 'mountain': 'MountainBikeRide', 'mountainbike': 'MountainBikeRide',
    'mountainbikeride': 'MountainBikeRide',
    'gravelcycling': 'GravelRide', 'gravel': 'GravelRide', 'gravelride': 'GravelRide',
    'ebikefitness': 'EBikeRide', 'ebike': 'EBikeRide', 'ebikeride': 'EBikeRide',
    'ebikemountain': 'EMountainBikeRide', 'emountainbikeride': 'EMountainBikeRide',
    'velomobile': 'Velomobile',
    'virtualride': 'VirtualRide', 'virtualcycling': 'VirtualRide',
    'swimming': 'Swim', 'swim': 'Swim', 'lapswimming': 'Swim', 'openwater': 'Swim',
    'canoeing': 'Canoeing', 'canoe': 'Canoeing',
    'kayaking': 'Kayaking', 'kayak': 'Kayaking',
    'kitesurfing': 'Kitesurfing', 'kitesurf': 'Kitesurfing', 'kiteboarding': 'Kitesurfing',
    'rowing': 'Rowing', 'row': 'Rowing',
    'standuppaddling': 'StandUpPaddling', 'paddling': 'StandUpPaddling', 'sup': 'StandUpPaddling',
    'surfing': 'Surfing', 'surf': 'Surfing',
    'windsurfing': 'Windsurfing', 'windsurf': 'Windsurfing',
    'sailing': 'Sailing', 'sail': 'Sailing',
    'iceskate': 'IceSkate', 'iceskating': 'IceSkate',
    'alpineski': 'AlpineSki', 'alpineskiing': 'AlpineSki', 'skiing': 'AlpineSki', 'downhillskiing': 'AlpineSki',
    'backcountryski': 'BackcountrySki', 'backcountry': 'BackcountrySki',
    'nordicski': 'NordicSki', 'crosscountryskiing': 'NordicSki', 'crosscountry': 'NordicSki',
    'snowboard': 'Snowboard', 'snowboarding': 'Snowboard',
    'snowshoe': 'Snowshoe', 'snowshoeing': 'Snowshoe',
    'handcycle': 'Handcycle', 'handcycling': 'Handcycle',
    'inlineskate': 'InlineSkate', 'inlineskating': 'InlineSkate',
    'rockclimbing': 'RockClimbing', 'rockclimb': 'RockClimbing', 'climbing': 'RockClimbing',
    'rollerski': 'RollerSki',
    'golf': 'Golf',
    'skateboard': 'Skateboard', 'skateboarding': 'Skateboard',
    'soccer': 'Soccer', 'football': 'Soccer',
    'wheelchair': 'Wheelchair',
    'badminton': 'Badminton',
    'tennis': 'Tennis',
    'pickleball': 'Pickleball',
    'crossfit': 'Crossfit',
    'elliptical': 'Elliptical',
    'stairstepper': 'StairStepper', 'stairclimbing': 'StairStepper',
    'weighttraining': 'WeightTraining', 'training': 'Workout', 'strengthtraining': 'WeightTraining',
    'yoga': 'Yoga',
    'workout': 'Workout', 'fitnessequipment': 'Workout', 'cardio': 'Workout',
    'hiit': 'HIIT', 'highintensityintervaltraining': 'HIIT',
    'pilates': 'Pilates',
    'tabletennis': 'TableTennis',
    'squash': 'Squash',
    'racquetball': 'Racquetball',
    'virtualrow': 'VirtualRow',
    # Old Strava GPX exports use numeric activity types.
    '1': 'Ride', '9': 'Run', '4': 'Hike', '10': 'Walk',
}

# Below this speed (m/s) an interval is a stop, by sport category.
_STOPPED_SPEED = {'running': 0.5, 'walking_hiking': 0.4, 'cycling': 1.0}
_DEFAULT_STOPPED_SPEED = 0.5


def normalize_sport_type(*raw_names: str | None) -> str:
    """
    The ``SPORT_TYPE_CHOICES`` key for the first sport name that matches, else ``'General'``.

    Pass the most specific name first (a FIT ``sub_sport``) and the broad one after it.
    """
    for raw in raw_names:
        if not raw:
            continue
        text = str(raw).strip()
        if text in _VALID:
            return text
        key = re.sub(r'[\s_\-]+', '', text).lower()
        if key in _ALIASES:
            return _ALIASES[key]
    return DEFAULT_SPORT


def stopped_speed_for(sport_type: str) -> float:
    """The speed (m/s) under which this sport counts as standing still."""
    for category, speed in _STOPPED_SPEED.items():
        if sport_type in SPORT_CATEGORIES[category]:
            return speed
    return _DEFAULT_STOPPED_SPEED
