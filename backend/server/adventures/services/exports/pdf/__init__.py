"""
Build a printable PDF from a Collection: a Trip Book for a trip, a Field Guide for a folder.

The trip book is for travelling with: cover, overview map, bookings and costs, then a page per day
with its own map and timeline. The field guide is a workbook for a folder of places: an overview
map, a checklist, and an entry per place with boxes to tick and lines to write on.
"""

from .builder import build_collection_pdf, pdf_filename_for_collection
from .data import get_collection_for_pdf
from .options import PdfOptions

__all__ = ['PdfOptions', 'build_collection_pdf', 'get_collection_for_pdf', 'pdf_filename_for_collection']
