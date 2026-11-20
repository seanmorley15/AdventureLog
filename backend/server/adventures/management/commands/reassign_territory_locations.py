from django.core.management.base import BaseCommand
from django.db import transaction

from adventures.models import Location
from adventures.services.geocoding.matching import find_region_for_point
from core.geo import point_to_lat_lon
from worldtravel.models import City, VisitedCity, VisitedRegion
from worldtravel.services import mark_cities_visited, mark_regions_visited


class Command(BaseCommand):
    help = (
        "Move places that sit in a region of a parent country onto the territory's own country. "
        "The world data lists some places twice, as a country and as a region of another one "
        "(Guadeloupe as a country and as a region of France). Places geocoded before the two were "
        "tied together were filed under the parent. Uses the world data only, with no provider "
        "calls. Dry run unless --apply is given."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist the changes (default is a dry run).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        locations = Location.objects.filter(region__territory__isnull=False).select_related(
            "user", "region__country", "region__territory", "city__region"
        )

        moves = []
        for location in locations:
            territory = location.region.territory
            if location.city and location.city.region.country_id == territory.id:
                # The world data import already moved this city onto the territory.
                new_city, new_region = location.city, location.city.region
            else:
                lat, lon = point_to_lat_lon(location.coordinates)
                new_region = find_region_for_point(territory.country_code, lat, lon)
                new_city = None
                if new_region and location.city:
                    new_city = City.objects.filter(
                        region__country=territory, name__iexact=location.city.name
                    ).first()
            moves.append((location, territory, new_region, new_city))
            self.stdout.write(
                f"{location.name} ({location.id}): {location.region.country.name} / {location.region.name} -> "
                f"{territory.name} / {new_region.name if new_region else 'no region'}"
            )

        if apply and moves:
            with transaction.atomic():
                self._apply(moves)

        verb = "Moved" if apply else "Would move"
        self.stdout.write(self.style.SUCCESS(f"{verb} {len(moves)} location(s)."))
        if moves and not apply:
            self.stdout.write("Re-run with --apply to save the changes.")

    def _apply(self, moves):
        left_regions = set()
        left_cities = set()
        for location, territory, new_region, new_city in moves:
            left_regions.add((location.user_id, location.region_id))
            if location.city_id:
                left_cities.add((location.user_id, location.city_id))

            # Queryset update avoids re-triggering geocoding and validation.
            Location.objects.filter(pk=location.pk).update(
                country=territory, region=new_region, city=new_city
            )
            if location.is_visited_status():
                if new_region:
                    mark_regions_visited(location.user_id, [new_region.id])
                if new_city:
                    mark_cities_visited(location.user_id, [new_city.id])

        # A visited row for the parent's region goes only when the user had a place moved out of
        # it and has none left there. One the user never had a place in may be a manual mark.
        for user_id, region_id in left_regions:
            if not Location.objects.filter(user_id=user_id, region_id=region_id).exists():
                VisitedRegion.objects.filter(user_id=user_id, region_id=region_id).delete()
        for user_id, city_id in left_cities:
            if not Location.objects.filter(user_id=user_id, city_id=city_id).exists():
                VisitedCity.objects.filter(user_id=user_id, city_id=city_id).delete()
