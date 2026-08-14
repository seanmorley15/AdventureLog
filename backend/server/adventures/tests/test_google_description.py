from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from adventures.providers.base import ProviderResult
from adventures.services.places.google_description import fetch_google_description


class GoogleDescriptionTests(SimpleTestCase):
    @override_settings(GOOGLE_MAPS_API_KEY='')
    def test_raises_when_google_maps_is_disabled(self):
        with self.assertRaises(RuntimeError):
            fetch_google_description('Acadia National Park')

    @override_settings(GOOGLE_MAPS_API_KEY='test-key')
    @patch('adventures.services.places.google_description.search_places')
    def test_uses_editorial_summary_from_search(self, mock_search):
        mock_search.return_value = ProviderResult(
            data=[
                {
                    'id': 'places/abc',
                    'displayName': {'text': 'Acadia National Park'},
                    'editorialSummary': {'text': 'A rugged coastal park on Mount Desert Island.'},
                }
            ]
        )

        result = fetch_google_description('Acadia National Park')

        self.assertIsNotNone(result)
        self.assertEqual(result['source'], 'google')
        self.assertIn('rugged coastal park', result['extract'])
        self.assertEqual(result['title'], 'Acadia National Park')
