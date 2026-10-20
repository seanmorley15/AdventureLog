"""Item kinds and ordering constants shared across the day plan."""

from __future__ import annotations




TEMP_ORDER_OFFSET = 1_000_000

SPAN_TYPES = ('lodging', 'transportation')

GLOBAL_TYPES = ('note', 'checklist')

PLACEABLE_TYPES = ('location', 'lodging', 'transportation', 'note', 'checklist')

TYPE_PRIORITY = {'lodging': 0, 'location': 1, 'transportation': 2, 'note': 3, 'checklist': 4}
