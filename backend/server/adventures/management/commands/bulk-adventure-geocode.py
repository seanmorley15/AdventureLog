"""The old name of ``bulk_location_geocode``, kept so existing scripts keep working."""

from adventures.management.commands.bulk_location_geocode import Command as _Command


class Command(_Command):
    def handle(self, *args, **options):
        self.stderr.write(self.style.WARNING("'bulk-adventure-geocode' is now 'bulk_location_geocode'; the old name will be removed."))
        return super().handle(*args, **options)
