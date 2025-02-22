import json
from django.core.management.base import BaseCommand
from achievements.models import Achievement

US_STATE_CODES = [
    'US-AL', 'US-AK', 'US-AZ', 'US-AR', 'US-CA', 'US-CO', 'US-CT', 'US-DE', 
    'US-FL', 'US-GA', 'US-HI', 'US-ID', 'US-IL', 'US-IN', 'US-IA', 'US-KS', 
    'US-KY', 'US-LA', 'US-ME', 'US-MD', 'US-MA', 'US-MI', 'US-MN', 'US-MS', 
    'US-MO', 'US-MT', 'US-NE', 'US-NV', 'US-NH', 'US-NJ', 'US-NM', 'US-NY', 
    'US-NC', 'US-ND', 'US-OH', 'US-OK', 'US-OR', 'US-PA', 'US-RI', 'US-SC', 
    'US-SD', 'US-TN', 'US-TX', 'US-UT', 'US-VT', 'US-VA', 'US-WA', 'US-WV', 
    'US-WI', 'US-WY'
]

ACHIEVEMENTS = [
    {
        "name": "First Adventure",
        "key": "achievements.first_adventure",
        "type": "adventure_count",
        "description": "Log your first adventure!",
        "condition": {"type": "adventure_count", "value": 1},
    },
    {
        "name": "Explorer",
        "key": "achievements.explorer",
        "type": "adventure_count",
        "description": "Log 10 adventures.",
        "condition": {"type": "adventure_count", "value": 10},
    },
    {
        "name": "Globetrotter",
        "key": "achievements.globetrotter",
        "type": "country_count",
        "description": "Visit 5 different countries.",
        "condition": {"type": "country_count", "value": 5},
    },
    {
        "name": "American Dream",
        "key": "achievements.american_dream",
        "type": "country_count",
        "description": "Visit all 50 states in the USA.",
        "condition": {"type": "country_count", "items": US_STATE_CODES},
    }
]




class Command(BaseCommand):
    help = "Seeds the database with predefined achievements"

    def handle(self, *args, **kwargs):
        for achievement_data in ACHIEVEMENTS:
            achievement, created = Achievement.objects.update_or_create(
                name=achievement_data["name"],
                defaults={
                    "description": achievement_data["description"],
                    "condition": json.dumps(achievement_data["condition"]),
                    "type": achievement_data["type"],
                    "key": achievement_data["key"],
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created: {achievement.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"🔄 Updated: {achievement.name}"))
