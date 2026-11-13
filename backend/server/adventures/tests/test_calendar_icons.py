from django.test import SimpleTestCase

from adventures.models.choices import TRANSPORTATION_TYPES
from adventures.services.calendar_events import TRANSPORT_ICONS


class TransportIconTests(SimpleTestCase):
    def test_every_transportation_type_but_other_has_a_calendar_icon(self):
        # The keys once said 'flight' while planes are stored as 'plane', so flights showed 🛣️.
        types = {value for value, _label in TRANSPORTATION_TYPES} - {'other'}
        self.assertEqual(set(TRANSPORT_ICONS), types)
