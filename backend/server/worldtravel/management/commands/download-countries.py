"""The old name of ``download_countries``, kept so existing scripts keep working."""

from worldtravel.management.commands.download_countries import Command as _Command


class Command(_Command):
    def handle(self, *args, **options):
        self.stderr.write(self.style.WARNING("'download-countries' is now 'download_countries'; the old name will be removed."))
        return super().handle(*args, **options)
