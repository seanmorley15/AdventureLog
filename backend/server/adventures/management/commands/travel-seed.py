"""The old name of ``travel_seed``, kept so existing scripts keep working."""

from adventures.management.commands.travel_seed import Command as _Command


class Command(_Command):
    def handle(self, *args, **options):
        self.stderr.write(self.style.WARNING("'travel-seed' is now 'travel_seed'; the old name will be removed."))
        return super().handle(*args, **options)
