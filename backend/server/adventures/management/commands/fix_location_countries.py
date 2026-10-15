from django.core.management.base import BaseCommand
from django.db.models import F, Q

from adventures.models import Location


class Command(BaseCommand):
    help = (
        "Repair locations whose country disagrees with their region/city. "
        "Older backup imports restored raw Country primary keys, which differ between "
        "installs and could attach the wrong country (e.g. Germany -> Ghana). "
        "The region/city country is authoritative. Dry run unless --apply is given."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist the corrections (default is a dry run).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        mismatched = (
            Location.objects.filter(country__isnull=False)
            .filter(
                Q(region__isnull=False) & ~Q(region__country_id=F("country_id"))
                | Q(region__isnull=True, city__isnull=False)
                & ~Q(city__region__country_id=F("country_id"))
            )
            .select_related("country", "region__country", "city__region__country")
        )

        fixed = 0
        for location in mismatched:
            correct = (
                location.region.country
                if location.region
                else location.city.region.country
            )
            self.stdout.write(
                f"{location.name} ({location.id}): {location.country.name} -> {correct.name}"
            )
            if apply:
                # Queryset update avoids re-triggering geocoding and validation.
                Location.objects.filter(pk=location.pk).update(country=correct)
            fixed += 1

        verb = "Fixed" if apply else "Would fix"
        self.stdout.write(self.style.SUCCESS(f"{verb} {fixed} location(s)."))
        if fixed and not apply:
            self.stdout.write("Re-run with --apply to save the changes.")
