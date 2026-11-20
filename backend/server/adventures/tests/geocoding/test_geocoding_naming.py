from django.test import SimpleTestCase

from adventures.services.geocoding.naming import first_preferred_location_name, looks_like_street_address


class StreetAddressDetectionTests(SimpleTestCase):
    """A street address is not a good name for a place; a landmark or business is."""

    ADDRESSES = [
        # English (how it always worked)
        '12 Main Street, Springfield',
        '221B Baker Street, London, UK',
        '1600 Pennsylvania Avenue NW',
        '742 Evergreen Terrace, Springfield, USA',
        # number first
        '12 Rue de Rivoli, 75001 Paris',
        '5 Avenida de la Constitución, Sevilla',
        '8 Calle Mayor, Madrid',
        '3 Via Roma, Milano',
        '14 Rua Augusta, Lisboa',
        '10 Chemin des Vignes, Lausanne',
        '27 Piazza Navona, Roma',
        # number last, the way much of Europe writes it
        'Hauptstraße 5, 10115 Berlin',
        'Friedrichstrasse 43-45, Berlin',
        'Rue de Rivoli 12, Paris',
        'Via Roma 12, Milano',
        'Calle Mayor 5, Madrid',
        'Kerkstraat 14, Amsterdam',
        'Storgatan 7, Stockholm',
        'Nørregade 10, København',
        'Ulica Floriańska 3, Kraków',
    ]
    NAMES = [
        'Eiffel Tower',
        'Musée du Louvre',
        'Louvre Museum',
        'Gare du Nord',
        'Café 21',
        'Route 66 Diner',
        'Rue Cases-Nègres (café)',
        'Via Ferrata Cima Ovest',
        'Hauptbahnhof',
        'Strandweg Beach Bar',
        'Plaza Hotel',
        '7 Eleven',
        'Piazza Navona',
        'Brandenburger Tor',
        'The Calle Ocho Cafe',
    ]

    def test_addresses_are_recognised_in_many_languages(self):
        for address in self.ADDRESSES:
            with self.subTest(address=address):
                self.assertTrue(looks_like_street_address(address))

    def test_landmarks_and_businesses_are_not_mistaken_for_addresses(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                self.assertFalse(looks_like_street_address(name))

    def test_a_foreign_address_is_skipped_in_favour_of_a_real_name(self):
        self.assertEqual(
            first_preferred_location_name(['12 Rue de Rivoli, 75001 Paris', 'Pyramide du Louvre']),
            'Pyramide du Louvre',
        )

    def test_a_foreign_address_is_only_used_when_allowed_as_a_last_resort(self):
        self.assertIsNone(first_preferred_location_name(['Hauptstraße 5, Berlin']))
        self.assertEqual(
            first_preferred_location_name(['Hauptstraße 5, Berlin'], allow_address_fallback=True),
            'Hauptstraße 5, Berlin',
        )
