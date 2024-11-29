from django.db import migrations

def migrate_categories(apps, schema_editor):
    # Use the historical models
    Adventure = apps.get_model('adventures', 'Adventure')
    Category = apps.get_model('adventures', 'Category')

    ADVENTURE_TYPES = {
        'general': ('General', '🌍'),
        'outdoor': ('Outdoor', '🏞️'),
        'lodging': ('Lodging', '🛌'),
        'dining': ('Dining', '🍽️'),
        'activity': ('Activity', '🏄'),
        'attraction': ('Attraction', '🎢'),
        'shopping': ('Shopping', '🛍️'),
        'nightlife': ('Nightlife', '🌃'),
        'event': ('Event', '🎉'),
        'transportation': ('Transportation', '🚗'),
        'culture': ('Culture', '🎭'),
        'water_sports': ('Water Sports', '🚤'),
        'hiking': ('Hiking', '🥾'),
        'wildlife': ('Wildlife', '🦒'),
        'historical_sites': ('Historical Sites', '🏛️'),
        'music_concerts': ('Music & Concerts', '🎶'),
        'fitness': ('Fitness', '🏋️'),
        'art_museums': ('Art & Museums', '🎨'),
        'festivals': ('Festivals', '🎪'),
        'spiritual_journeys': ('Spiritual Journeys', '🧘‍♀️'),
        'volunteer_work': ('Volunteer Work', '🤝'),
        'other': ('Other', '❓'),
    }   
    
    adventures = Adventure.objects.all()
    for adventure in adventures:
        # Access the old 'type' field using __dict__ because it's not in the model anymore
        old_type = adventure.__dict__.get('type')
        if old_type in ADVENTURE_TYPES:
            category, created = Category.objects.get_or_create(
                name=old_type,
                user_id=adventure.user_id,
                defaults={
                    'display_name': ADVENTURE_TYPES[old_type][0],
                    'icon': ADVENTURE_TYPES[old_type][1],
                }
            )
            adventure.category = category
            adventure.save()
        else:
            print(f"Unknown type: {old_type}")

class Migration(migrations.Migration):

    dependencies = [
        ('adventures', '0011_category_adventure_category'),
    ]

    operations = [
        migrations.RunPython(migrate_categories),
    ]