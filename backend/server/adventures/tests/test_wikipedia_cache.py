from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from adventures.services.wikipedia.description_service import WikipediaDescriptionService


@override_settings(WIKIPEDIA_DESC_CACHE_TIMEOUT=3600)
class WikipediaDescriptionCacheTests(SimpleTestCase):
    @patch('adventures.services.wikipedia.description_service.get_or_fetch_cached')
    def test_get_description_uses_cache(self, mock_get_or_fetch_cached):
        mock_get_or_fetch_cached.return_value = {'extract': 'A sample description', 'title': 'Paris'}

        service = WikipediaDescriptionService()
        result = service.get_description('Paris', 'en')

        self.assertEqual(result['extract'], 'A sample description')
        mock_get_or_fetch_cached.assert_called_once()
        args = mock_get_or_fetch_cached.call_args.args
        self.assertEqual(args[0], 'wikipedia_desc_v1')
        self.assertEqual(args[1], 'en')
        self.assertEqual(args[2], 'Paris')
