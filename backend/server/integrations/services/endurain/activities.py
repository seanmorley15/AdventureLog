"""Turning an Endurain activity into the fields an AdventureLog activity has."""


from .connection import format_server_url


ACTIVITY_TYPE_MAP = {
    1: 'Run',
    2: 'Run',
    3: 'Run',
    4: 'Ride',
    5: 'Ride',
    6: 'Ride',
    7: 'Ride',
    8: 'Swim',
    9: 'Swim',
    10: 'Workout',
    11: 'Walk',
    12: 'Hike',
    13: 'Rowing',
    14: 'Yoga',
    15: 'AlpineSki',
    16: 'NordicSki',
    17: 'Snowboard',
    18: 'Transition',
    19: 'Workout',
    20: 'Crossfit',
    21: 'Tennis',
    22: 'TableTennis',
    23: 'Badminton',
    24: 'Squash',
    25: 'Racquetball',
    26: 'Pickleball',
    27: 'Ride',
    28: 'Ride',
    29: 'Ride',
    30: 'Windsurf',
    31: 'Walk',
    32: 'StandUpPaddling',
    33: 'Surf',
    34: 'Run',
    35: 'Ride',
    36: 'Ride',
    37: 'IceSkate',
    38: 'Soccer',
    39: 'Padel',
    40: 'Run',
    41: 'Workout',
    42: 'Kayaking',
    43: 'Sailing',
    44: 'Snowshoe',
    45: 'InlineSkate',
    46: 'HIIT',
    47: 'JumpRope',
}


def _sport_type_name(activity_type: int | None) -> str:
    if activity_type is None:
        return 'Activity'
    return ACTIVITY_TYPE_MAP.get(int(activity_type), 'Activity')


def normalize_activity(activity: dict, server_url: str) -> dict:
    activity_id = activity.get('id')
    distance = float(activity.get('distance') or 0)
    moving_time = activity.get('total_timer_time') or activity.get('total_elapsed_time') or 0
    elapsed_time = activity.get('total_elapsed_time') or moving_time or 0
    moving_time = int(moving_time) if moving_time else 0
    elapsed_time = int(elapsed_time) if elapsed_time else 0
    rest_time = max(0, elapsed_time - moving_time) if elapsed_time and moving_time else 0

    avg_speed = activity.get('average_speed')
    max_speed = activity.get('max_speed')
    elevation_gain = activity.get('elevation_gain')
    elevation_loss = activity.get('elevation_loss')
    if elevation_gain is not None:
        elevation_gain = float(elevation_gain)
    if elevation_loss is not None:
        elevation_loss = float(elevation_loss)
    activity_type = activity.get('activity_type')
    sport_type = _sport_type_name(activity_type)

    start_date = activity.get('start_time') or activity.get('start_time_tz_applied') or ''
    start_date_local = activity.get('start_time_tz_applied') or start_date

    pace_per_km = None
    pace_per_mile = None
    if moving_time and distance > 0:
        pace_per_km = moving_time / (distance / 1000)
        pace_per_mile = moving_time / (distance / 1609.34)

    base_url = format_server_url(server_url)
    export_gpx = f'/api/integrations/endurain/activities/{activity_id}/gpx/'

    return {
        'id': activity_id,
        'name': activity.get('name') or 'Activity',
        'type': sport_type,
        'sport_type': sport_type,
        'distance': distance,
        'distance_km': round(distance / 1000, 2) if distance else None,
        'distance_miles': round(distance / 1609.34, 2) if distance else None,
        'moving_time': moving_time,
        'elapsed_time': elapsed_time,
        'rest_time': rest_time,
        'total_elevation_gain': elevation_gain,
        'estimated_elevation_loss': elevation_loss,
        'elev_high': None,
        'elev_low': None,
        'total_elevation_range': None,
        'start_date': start_date,
        'start_date_local': start_date_local,
        'timezone': activity.get('timezone') or '',
        'timezone_raw': activity.get('timezone') or '',
        'average_speed': avg_speed,
        'average_speed_kmh': round(avg_speed * 3.6, 2) if avg_speed else None,
        'average_speed_mph': round(avg_speed * 2.237, 2) if avg_speed else None,
        'max_speed': max_speed,
        'max_speed_kmh': round(max_speed * 3.6, 2) if max_speed else None,
        'max_speed_mph': round(max_speed * 2.237, 2) if max_speed else None,
        'pace_per_km_seconds': pace_per_km,
        'pace_per_mile_seconds': pace_per_mile,
        'grade_adjusted_average_speed': None,
        'average_cadence': activity.get('average_cad'),
        'average_watts': activity.get('average_power'),
        'max_watts': activity.get('max_power'),
        'kilojoules': None,
        'calories': activity.get('calories'),
        'achievement_count': 0,
        'kudos_count': 0,
        'comment_count': 0,
        'pr_count': 0,
        'gear_id': str(activity.get('gear_id')) if activity.get('gear_id') else None,
        'device_name': activity.get('tracker_model') or activity.get('tracker_manufacturer'),
        'trainer': False,
        'manual': False,
        'start_latlng': None,
        'end_latlng': None,
        'export_original': f'{base_url}/activity/{activity_id}',
        'export_gpx': export_gpx,
        'visibility': str(activity.get('visibility', '')),
        'photo_count': 0,
        'has_heartrate': activity.get('average_hr') is not None,
        'flagged': False,
        'commute': False,
        'provider': 'endurain',
    }
