from main.settings import CITIES_LOCALES
from worldtravel.models import Country
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Get translations for all countries'

    def handle(self, *args, **options):
        countries = Country.objects.all()
        countries_to_update = []
        for country in countries:
            updated = country.get_translations(CITIES_LOCALES)
            if updated:
                countries_to_update.append(country)
        # Bulk update the translations
        Country.objects.bulk_update(countries_to_update, ['translations'])
        print(f"Updated translations for {len(countries_to_update)} countries")