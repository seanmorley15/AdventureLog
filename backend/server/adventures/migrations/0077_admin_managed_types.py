from django.db import migrations, models


def populate_transportation_types(apps, schema_editor):
    TransportationType = apps.get_model('adventures', 'TransportationType')
    types = [
        ('car', 'Car', '🚗', 1),
        ('plane', 'Plane', '✈️', 2),
        ('train', 'Train', '🚆', 3),
        ('bus', 'Bus', '🚌', 4),
        ('boat', 'Boat', '⛵', 5),
        ('bike', 'Bike', '🚲', 6),
        ('walking', 'Walking', '🚶', 7),
        ('cab', 'Cab', '🚕', 8),
        ('vtc', 'VTC', '🚙', 9),
        ('other', 'Other', '❓', 100),
    ]
    for key, name, icon, order in types:
        TransportationType.objects.get_or_create(
            key=key,
            defaults={'name': name, 'icon': icon, 'display_order': order, 'is_active': True}
        )


def populate_lodging_types(apps, schema_editor):
    LodgingType = apps.get_model('adventures', 'LodgingType')
    types = [
        ('hotel', 'Hotel', '🏨', 1),
        ('hostel', 'Hostel', '🛏️', 2),
        ('resort', 'Resort', '🏝️', 3),
        ('bnb', 'Bed & Breakfast', '🍳', 4),
        ('campground', 'Campground', '🏕️', 5),
        ('cabin', 'Cabin', '🏚️', 6),
        ('apartment', 'Apartment', '🏢', 7),
        ('house', 'House', '🏠', 8),
        ('villa', 'Villa', '🏡', 9),
        ('motel', 'Motel', '🚗🏨', 10),
        ('other', 'Other', '❓', 100),
    ]
    for key, name, icon, order in types:
        LodgingType.objects.get_or_create(
            key=key,
            defaults={'name': name, 'icon': icon, 'display_order': order, 'is_active': True}
        )


def populate_activity_types(apps, schema_editor):
    ActivityType = apps.get_model('adventures', 'ActivityType')
    types = [
        ('general', 'General', '🌍', 1),
        ('outdoor', 'Outdoor', '🏞️', 2),
        ('lodging', 'Lodging', '🛌', 3),
        ('dining', 'Dining', '🍽️', 4),
        ('activity', 'Activity', '🏄', 5),
        ('attraction', 'Attraction', '🎢', 6),
        ('shopping', 'Shopping', '🛍️', 7),
        ('nightlife', 'Nightlife', '🌃', 8),
        ('event', 'Event', '🎉', 9),
        ('transportation', 'Transportation', '🚗', 10),
        ('culture', 'Culture', '🎭', 11),
        ('water_sports', 'Water Sports', '🚤', 12),
        ('hiking', 'Hiking', '🥾', 13),
        ('wildlife', 'Wildlife', '🦒', 14),
        ('historical_sites', 'Historical Sites', '🏛️', 15),
        ('music_concerts', 'Music & Concerts', '🎶', 16),
        ('fitness', 'Fitness', '🏋️', 17),
        ('art_museums', 'Art & Museums', '🎨', 18),
        ('festivals', 'Festivals', '🎪', 19),
        ('spiritual_journeys', 'Spiritual Journeys', '🧘‍♀️', 20),
        ('volunteer_work', 'Volunteer Work', '🤝', 21),
        ('other', 'Other', '❓', 100),
    ]
    for key, name, icon, order in types:
        ActivityType.objects.get_or_create(
            key=key,
            defaults={'name': name, 'icon': icon, 'display_order': order, 'is_active': True}
        )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0076_entity_system_overhaul'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransportationType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text="Unique identifier (e.g., 'plane', 'train')", max_length=50, unique=True)),
                ('name', models.CharField(help_text="Display name (e.g., 'Plane', 'Train')", max_length=100)),
                ('icon', models.CharField(help_text="Emoji icon (e.g., '✈️', '🚆')", max_length=10)),
                ('display_order', models.IntegerField(default=0, help_text='Order in dropdown lists')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this type is available for selection')),
            ],
            options={
                'verbose_name': 'Transportation Type',
                'verbose_name_plural': 'Transportation Types',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='LodgingType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text="Unique identifier (e.g., 'hotel', 'hostel')", max_length=50, unique=True)),
                ('name', models.CharField(help_text="Display name (e.g., 'Hotel', 'Hostel')", max_length=100)),
                ('icon', models.CharField(help_text="Emoji icon (e.g., '🏨', '🛏️')", max_length=10)),
                ('display_order', models.IntegerField(default=0, help_text='Order in dropdown lists')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this type is available for selection')),
            ],
            options={
                'verbose_name': 'Lodging Type',
                'verbose_name_plural': 'Lodging Types',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ActivityType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text="Unique identifier (e.g., 'hiking', 'dining')", max_length=50, unique=True)),
                ('name', models.CharField(help_text="Display name (e.g., 'Hiking', 'Dining')", max_length=100)),
                ('icon', models.CharField(help_text="Emoji icon (e.g., '🥾', '🍽️')", max_length=10)),
                ('display_order', models.IntegerField(default=0, help_text='Order in dropdown lists')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this type is available for selection')),
            ],
            options={
                'verbose_name': 'Activity Type',
                'verbose_name_plural': 'Activity Types',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.RunPython(populate_transportation_types, reverse_noop),
        migrations.RunPython(populate_lodging_types, reverse_noop),
        migrations.RunPython(populate_activity_types, reverse_noop),
    ]
