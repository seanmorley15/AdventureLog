from django.db import migrations, models


def populate_activity_types(apps, schema_editor):
    """Populate ActivityType with sport types."""
    ActivityType = apps.get_model('adventures', 'ActivityType')

    sport_types = [
        # General Sports
        ('General', 'General', '🏃', '#6B7280', 1),

        # Foot Sports
        ('Run', 'Run', '🏃‍♂️', '#F59E0B', 10),
        ('TrailRun', 'Trail Run', '🏃‍♀️', '#F59E0B', 11),
        ('Walk', 'Walk', '🚶', '#8B5CF6', 12),
        ('Hike', 'Hike', '🥾', '#10B981', 13),
        ('VirtualRun', 'Virtual Run', '💻', '#F59E0B', 14),

        # Cycle Sports
        ('Ride', 'Ride', '🚴', '#3B82F6', 20),
        ('MountainBikeRide', 'Mountain Bike Ride', '🚵', '#3B82F6', 21),
        ('GravelRide', 'Gravel Ride', '🚴‍♀️', '#3B82F6', 22),
        ('EBikeRide', 'E-Bike Ride', '🔋', '#3B82F6', 23),
        ('EMountainBikeRide', 'E-Mountain Bike Ride', '⚡', '#3B82F6', 24),
        ('Velomobile', 'Velomobile', '🚲', '#3B82F6', 25),
        ('VirtualRide', 'Virtual Ride', '🖥️', '#3B82F6', 26),

        # Water Sports
        ('Canoeing', 'Canoe', '🛶', '#06B6D4', 30),
        ('Kayaking', 'Kayak', '🛶', '#06B6D4', 31),
        ('Kitesurfing', 'Kitesurf', '🪁', '#06B6D4', 32),
        ('Rowing', 'Rowing', '🚣', '#06B6D4', 33),
        ('StandUpPaddling', 'Stand Up Paddling', '🏄', '#3B82F6', 34),
        ('Surfing', 'Surf', '🏄‍♂️', '#06B6D4', 35),
        ('Swim', 'Swim', '🏊', '#06B6D4', 36),
        ('Windsurfing', 'Windsurf', '🏄‍♀️', '#06B6D4', 37),
        ('Sailing', 'Sail', '⛵', '#06B6D4', 38),

        # Winter Sports
        ('IceSkate', 'Ice Skate', '⛸️', '#0EA5E9', 40),
        ('AlpineSki', 'Alpine Ski', '⛷️', '#0EA5E9', 41),
        ('BackcountrySki', 'Backcountry Ski', '🎿', '#0EA5E9', 42),
        ('NordicSki', 'Nordic Ski', '🎿', '#0EA5E9', 43),
        ('Snowboard', 'Snowboard', '🏂', '#0EA5E9', 44),
        ('Snowshoe', 'Snowshoe', '🥾', '#0EA5E9', 45),

        # Other Sports
        ('Handcycle', 'Handcycle', '🚴‍♂️', '#EF4444', 50),
        ('InlineSkate', 'Inline Skate', '🛼', '#8B5CF6', 51),
        ('RockClimbing', 'Rock Climb', '🧗', '#DC2626', 52),
        ('RollerSki', 'Roller Ski', '🎿', '#F97316', 53),
        ('Golf', 'Golf', '⛳', '#22C55E', 54),
        ('Skateboard', 'Skateboard', '🛹', '#F59E0B', 55),
        ('Soccer', 'Football (Soccer)', '⚽', '#10B981', 56),
        ('Wheelchair', 'Wheelchair', '♿', '#3B82F6', 57),
        ('Badminton', 'Badminton', '🏸', '#F59E0B', 58),
        ('Tennis', 'Tennis', '🎾', '#10B981', 59),
        ('Pickleball', 'Pickleball', '🏓', '#F59E0B', 60),
        ('Crossfit', 'Crossfit', '💪', '#DC2626', 61),
        ('Elliptical', 'Elliptical', '🏃‍♀️', '#8B5CF6', 62),
        ('StairStepper', 'Stair Stepper', '🪜', '#6B7280', 63),
        ('WeightTraining', 'Weight Training', '🏋️', '#DC2626', 64),
        ('Yoga', 'Yoga', '🧘', '#8B5CF6', 65),
        ('Workout', 'Workout', '💪', '#EF4444', 66),
        ('HIIT', 'HIIT', '⚡', '#F59E0B', 67),
        ('Pilates', 'Pilates', '🧘‍♀️', '#8B5CF6', 68),
        ('TableTennis', 'Table Tennis', '🏓', '#F59E0B', 69),
        ('Squash', 'Squash', '🎾', '#F59E0B', 70),
        ('Racquetball', 'Racquetball', '🎾', '#F59E0B', 71),
        ('VirtualRow', 'Virtual Rowing', '🚣‍♂️', '#06B6D4', 72),
    ]

    for key, name, icon, color, order in sport_types:
        ActivityType.objects.get_or_create(
            key=key,
            defaults={'name': name, 'icon': icon, 'color': color, 'display_order': order, 'is_active': True}
        )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0077_admin_managed_types'),
    ]

    operations = [
        # First rename the table directly to avoid index conflicts
        migrations.RunSQL(
            sql='ALTER TABLE adventures_activitytype RENAME TO adventures_adventuretype;',
            reverse_sql='ALTER TABLE adventures_adventuretype RENAME TO adventures_activitytype;',
        ),
        # Drop the old unique constraint/index
        migrations.RunSQL(
            sql='DROP INDEX IF EXISTS adventures_activitytype_key_a53223c5_like;',
            reverse_sql='',
        ),
        migrations.RunSQL(
            sql='ALTER INDEX IF EXISTS adventures_activitytype_pkey RENAME TO adventures_adventuretype_pkey;',
            reverse_sql='ALTER INDEX IF EXISTS adventures_adventuretype_pkey RENAME TO adventures_activitytype_pkey;',
        ),
        migrations.RunSQL(
            sql='ALTER INDEX IF EXISTS adventures_activitytype_key_key RENAME TO adventures_adventuretype_key_key;',
            reverse_sql='ALTER INDEX IF EXISTS adventures_adventuretype_key_key RENAME TO adventures_activitytype_key_key;',
        ),
        # Update the model state
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameModel(
                    old_name='ActivityType',
                    new_name='AdventureType',
                ),
            ],
            database_operations=[],
        ),
        migrations.AlterModelOptions(
            name='adventuretype',
            options={'ordering': ['display_order', 'name'], 'verbose_name': 'Adventure Type', 'verbose_name_plural': 'Adventure Types'},
        ),

        # Create new ActivityType for sports
        migrations.CreateModel(
            name='ActivityType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text="Unique identifier (e.g., 'Run', 'Hike')", max_length=50, unique=True)),
                ('name', models.CharField(help_text="Display name (e.g., 'Run', 'Hike')", max_length=100)),
                ('icon', models.CharField(help_text="Emoji icon (e.g., '🏃', '🥾')", max_length=10)),
                ('color', models.CharField(default='#6B7280', help_text="Color code (e.g., '#F59E0B')", max_length=20)),
                ('display_order', models.IntegerField(default=0, help_text='Order in dropdown lists')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this type is available for selection')),
            ],
            options={
                'verbose_name': 'Activity Type',
                'verbose_name_plural': 'Activity Types',
                'ordering': ['display_order', 'name'],
            },
        ),

        # Populate ActivityType with sport types
        migrations.RunPython(populate_activity_types, reverse_noop),
    ]
