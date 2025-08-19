SPORT_TYPE_CHOICES = [
    # General Sports
    ('General', 'General'),

    # Foot Sports
    ('Run', 'Run'),
    ('TrailRun', 'Trail Run'),
    ('Walk', 'Walk'),
    ('Hike', 'Hike'),
    ('VirtualRun', 'Virtual Run'),

    # Cycle Sports
    ('Ride', 'Ride'),
    ('MountainBikeRide', 'Mountain Bike Ride'),
    ('GravelRide', 'Gravel Ride'),
    ('EBikeRide', 'E-Bike Ride'),
    ('EMountainBikeRide', 'E-Mountain Bike Ride'),
    ('Velomobile', 'Velomobile'),
    ('VirtualRide', 'Virtual Ride'),

    # Water Sports
    ('Canoeing', 'Canoe'),
    ('Kayaking', 'Kayak'),
    ('Kitesurfing', 'Kitesurf'),
    ('Rowing', 'Rowing'),
    ('StandUpPaddling', 'Stand Up Paddling'),
    ('Surfing', 'Surf'),
    ('Swim', 'Swim'),
    ('Windsurfing', 'Windsurf'),
    ('Sailing', 'Sail'),

    # Winter Sports
    ('IceSkate', 'Ice Skate'),
    ('AlpineSki', 'Alpine Ski'),
    ('BackcountrySki', 'Backcountry Ski'),
    ('NordicSki', 'Nordic Ski'),
    ('Snowboard', 'Snowboard'),
    ('Snowshoe', 'Snowshoe'),

    # Other Sports
    ('Handcycle', 'Handcycle'),
    ('InlineSkate', 'Inline Skate'),
    ('RockClimbing', 'Rock Climb'),
    ('RollerSki', 'Roller Ski'),
    ('Golf', 'Golf'),
    ('Skateboard', 'Skateboard'),
    ('Soccer', 'Football (Soccer)'),
    ('Wheelchair', 'Wheelchair'),
    ('Badminton', 'Badminton'),
    ('Tennis', 'Tennis'),
    ('Pickleball', 'Pickleball'),
    ('Crossfit', 'Crossfit'),
    ('Elliptical', 'Elliptical'),
    ('StairStepper', 'Stair Stepper'),
    ('WeightTraining', 'Weight Training'),
    ('Yoga', 'Yoga'),
    ('Workout', 'Workout'),
    ('HIIT', 'HIIT'),
    ('Pilates', 'Pilates'),
    ('TableTennis', 'Table Tennis'),
    ('Squash', 'Squash'),
    ('Racquetball', 'Racquetball'),
    ('VirtualRow', 'Virtual Rowing'),
]

SPORT_CATEGORIES = {
    'running': ['Run', 'TrailRun', 'VirtualRun'],
    'walking_hiking': ['Walk', 'Hike'],
    'cycling': ['Ride', 'MountainBikeRide', 'GravelRide', 'EBikeRide', 'EMountainBikeRide', 'Velomobile', 'VirtualRide'],
    'water_sports': ['Canoeing', 'Kayaking', 'Kitesurfing', 'Rowing', 'StandUpPaddling', 'Surfing', 'Swim', 'Windsurfing', 'Sailing', 'VirtualRow'],
    'winter_sports': ['IceSkate', 'AlpineSki', 'BackcountrySki', 'NordicSki', 'Snowboard', 'Snowshoe'],
    'fitness_gym': ['Crossfit', 'Elliptical', 'StairStepper', 'WeightTraining', 'Yoga', 'Workout', 'HIIT', 'Pilates'],
    'racket_sports': ['Badminton', 'Tennis', 'Pickleball', 'TableTennis', 'Squash', 'Racquetball'],
    'climbing_adventure': ['RockClimbing'],
    'team_sports': ['Soccer'],
    'other_sports': ['Handcycle', 'InlineSkate', 'RollerSki', 'Golf', 'Skateboard', 'Wheelchair', 'General']
    }