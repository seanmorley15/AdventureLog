"""Putting stored files into a backup archive."""

import logging

from django.core.files.storage import default_storage

from .serialization import storage_basename

logger = logging.getLogger(__name__)

IMAGES = 'images'
ATTACHMENTS = 'attachments'
GPX = 'gpx'


class ArchiveMedia:
    """Writes each stored file into the archive once, under ``<folder>/<file name>``."""

    def __init__(self, archive):
        self.archive = archive
        self.added = set()

    def add(self, folder, storage_name):
        if not storage_name or storage_name in self.added:
            return
        try:
            with default_storage.open(storage_name) as stored:
                self.archive.writestr(f'{folder}/{storage_basename(storage_name)}', stored.read())
        except Exception:
            # A missing file should not make the rest of the backup unusable.
            logger.warning('Could not add %s to the backup', storage_name, exc_info=True)
            return
        self.added.add(storage_name)

    def add_image(self, image):
        if image.image:
            self.add(IMAGES, image.image.name)

    def add_attachment(self, attachment):
        if attachment.file:
            self.add(ATTACHMENTS, attachment.file.name)

    def add_gpx(self, activity):
        if activity.gpx_file:
            self.add(GPX, activity.gpx_file.name)
