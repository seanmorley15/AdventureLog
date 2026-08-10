from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from adventures.providers.base import ProviderResult
from adventures.services.places.search import search_places


class ProviderSelectionTests(SimpleTestCase):
    @override_settings(GOOGLE_MAPS_API_KEY="test-key")
    @patch("adventures.services.places.search.osm_search")
    @patch("adventures.services.places.search.google_search")
    def test_search_places_prefers_google_when_scores_higher(self, mock_google, mock_osm):
        mock_google.return_value = ProviderResult(
            data=[
                {
                    "id": "g-1",
                    "displayName": {"text": "Central Park"},
                    "formattedAddress": "Central Park, NY",
                    "location": {"latitude": 40.785091, "longitude": -73.968285},
                    "types": ["park"],
                    "rating": 4.7,
                    "userRatingCount": 1200,
                }
            ]
        )
        mock_osm.return_value = ProviderResult(
            data=[
                {
                    "name": "Central Park",
                    "display_name": "Central Park, Manhattan",
                    "lat": "40.785091",
                    "lon": "-73.968285",
                    "importance": 0.4,
                    "type": "park",
                    "category": "leisure",
                    "addresstype": "park",
                }
            ]
        )

        selection = search_places("40.78,-73.96")

        self.assertIsNone(selection.error)
        self.assertEqual(selection.provider_used, "google")
        self.assertTrue(selection.results)

    @override_settings(GOOGLE_MAPS_API_KEY="test-key")
    @patch("adventures.services.places.search.osm_search")
    @patch("adventures.services.places.search.google_search")
    def test_search_places_falls_back_to_osm_when_google_errors(self, mock_google, mock_osm):
        mock_google.return_value = ProviderResult(error="Google unavailable")
        mock_osm.return_value = ProviderResult(
            data=[
                {
                    "name": "Lisbon",
                    "display_name": "Lisbon, Portugal",
                    "lat": "38.7223",
                    "lon": "-9.1393",
                    "importance": 0.6,
                    "type": "city",
                    "category": "place",
                    "addresstype": "city",
                }
            ]
        )

        selection = search_places("Lisbon")

        self.assertIsNone(selection.error)
        self.assertEqual(selection.provider_used, "osm")
        self.assertTrue(selection.results)

    @override_settings(GOOGLE_MAPS_API_KEY="test-key")
    @patch("adventures.services.places.search.osm_search")
    @patch("adventures.services.places.search.google_search")
    def test_search_places_returns_mixed_when_scores_close(self, mock_google, mock_osm):
        mock_google.return_value = ProviderResult(
            data=[
                {
                    "id": "g-2",
                    "displayName": {"text": "Sydney"},
                    "formattedAddress": "Sydney, Australia",
                    "location": {"latitude": -33.8688, "longitude": 151.2093},
                    "types": ["locality"],
                }
            ]
        )
        mock_osm.return_value = ProviderResult(
            data=[
                {
                    "name": "Sydney",
                    "display_name": "Sydney, NSW, Australia",
                    "lat": "-33.8688",
                    "lon": "151.2093",
                    "importance": 0.648,
                    "type": "city",
                    "category": "place",
                    "addresstype": "city",
                }
            ]
        )

        selection = search_places("-33.86,151.20")

        self.assertIsNone(selection.error)
        self.assertEqual(selection.provider_used, "mixed")
        self.assertTrue(selection.results)
