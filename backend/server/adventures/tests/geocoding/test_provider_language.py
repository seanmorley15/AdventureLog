"""The user's UI language reaches OpenStreetMap, Google details and Wikipedia."""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from adventures.providers.geocoding.osm import reverse_geocode
from adventures.providers.places.osm import search_places as osm_search_places
from adventures.providers.wikipedia import fetch_summary
from adventures.services.places.search import ProviderSearchResult, search_places as search_places_service
from adventures.services.quick_add import extract_google_place_details
from adventures.utils.language import resolve_request_language
from core.results import ProviderResult
from core.testing import make_user


def _response(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class ResolveRequestLanguageTests(SimpleTestCase):
    def _request(self, path='/api/places/search/', **headers):
        return Request(APIRequestFactory().get(path, **headers))

    def test_query_param_wins(self):
        request = self._request('/api/places/details/?lang=de', HTTP_X_ADVENTURELOG_LOCALE='ja')
        self.assertEqual(resolve_request_language(request), 'de')

    def test_ui_locale_header(self):
        self.assertEqual(resolve_request_language(self._request(HTTP_X_ADVENTURELOG_LOCALE='pt-BR')), 'pt-BR')

    def test_locale_cookie_for_direct_clients(self):
        self.assertEqual(resolve_request_language(self._request(HTTP_COOKIE='locale=ja')), 'ja')

    def test_accept_language_uses_first_entry(self):
        request = self._request(HTTP_ACCEPT_LANGUAGE='fr-CA,fr;q=0.9,en;q=0.8')
        self.assertEqual(resolve_request_language(request), 'fr-CA')

    @override_settings(LANGUAGE_CODE='en-us')
    def test_invalid_values_fall_back_to_language_code(self):
        request = self._request(HTTP_X_ADVENTURELOG_LOCALE='bad header', HTTP_ACCEPT_LANGUAGE='*')
        self.assertEqual(resolve_request_language(request), 'en-us')


class OSMProviderLanguageTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch('adventures.providers.places.osm.requests.get')
    def test_places_sends_accept_language(self, mock_get):
        mock_get.return_value = _response([{'name': 'Tokyo'}])
        osm_search_places('Tokyo', language='ja')
        self.assertEqual(mock_get.call_args.kwargs['headers']['Accept-Language'], 'ja')

    @patch('adventures.providers.places.osm.requests.get')
    def test_places_omits_accept_language_by_default(self, mock_get):
        mock_get.return_value = _response([{'name': 'Tokyo'}])
        osm_search_places('Tokyo')
        self.assertNotIn('Accept-Language', mock_get.call_args.kwargs['headers'])

    @patch('adventures.providers.places.osm.requests.get')
    def test_places_cache_is_per_language(self, mock_get):
        """A result cached for one language must not be served to someone who reads another."""
        mock_get.side_effect = [_response([{'name': 'Tokyo'}]), _response([{'name': '東京'}])]

        english = osm_search_places('Tokyo', language='en')
        japanese = osm_search_places('Tokyo', language='ja')
        japanese_again = osm_search_places('Tokyo', language='ja')

        self.assertEqual(english.data[0]['name'], 'Tokyo')
        self.assertEqual(japanese.data[0]['name'], '東京')
        self.assertEqual(japanese_again.data[0]['name'], '東京')
        self.assertEqual(mock_get.call_count, 2)

    @patch('adventures.providers.geocoding.osm.is_resolvable', return_value=True)
    @patch('adventures.providers.geocoding.osm.requests.get')
    def test_reverse_geocode_sends_accept_language(self, mock_get, _resolvable):
        mock_get.return_value = _response({'name': 'x'})
        reverse_geocode(35.0, 139.0, language='ja')
        self.assertEqual(mock_get.call_args.kwargs['headers']['Accept-Language'], 'ja')

    @patch('adventures.providers.geocoding.osm.is_resolvable', return_value=True)
    @patch('adventures.providers.geocoding.osm.requests.get')
    def test_reverse_geocode_cache_is_per_language(self, mock_get, _resolvable):
        mock_get.side_effect = [_response({'name': 'Tokyo'}), _response({'name': '東京'})]

        english = reverse_geocode(35.0, 139.0, language='en')
        japanese = reverse_geocode(35.0, 139.0, language='ja')

        self.assertEqual(english.data['name'], 'Tokyo')
        self.assertEqual(japanese.data['name'], '東京')
        self.assertEqual(mock_get.call_count, 2)


class ServiceLanguageTests(SimpleTestCase):
    @override_settings(GOOGLE_MAPS_API_KEY='')
    @patch('adventures.services.places.search.osm_search')
    def test_search_passes_language_to_osm(self, mock_osm):
        mock_osm.return_value = ProviderResult(data=[])
        search_places_service('Tokyo', language='ja')
        mock_osm.assert_called_once_with('Tokyo', limit=20, language='ja')


class PlacesViewLanguageTests(TestCase):
    def setUp(self):
        self.user = make_user('traveller')
        self.client.force_login(self.user)

    @patch('adventures.views.places.search_places')
    def test_search_forwards_ui_locale(self, mock_search):
        mock_search.return_value = ProviderSearchResult(provider_used='osm', results=[])
        response = self.client.get('/api/places/search/', {'q': 'Tokyo'}, HTTP_X_ADVENTURELOG_LOCALE='ja')
        self.assertEqual(response.status_code, 200)
        mock_search.assert_called_once_with('Tokyo', language='ja')

    @patch('adventures.views.places.get_place_details')
    def test_details_forwards_ui_locale(self, mock_details):
        mock_details.return_value = {'description': 'A place'}
        response = self.client.get(
            '/api/places/details/', {'place_id': 'abc', 'name': 'Tokyo'}, HTTP_X_ADVENTURELOG_LOCALE='ja'
        )
        self.assertEqual(response.status_code, 200)
        mock_details.assert_called_once_with('abc', fallback_query='Tokyo', language='ja')

    @patch('adventures.views.places.get_place_details')
    def test_details_explicit_lang_wins(self, mock_details):
        mock_details.return_value = {'description': 'A place'}
        self.client.get(
            '/api/places/details/', {'place_id': 'abc', 'lang': 'de'}, HTTP_X_ADVENTURELOG_LOCALE='ja'
        )
        mock_details.assert_called_once_with('abc', fallback_query='', language='de')

    @patch('adventures.views.places.reverse_geocode')
    def test_reverse_forwards_ui_locale(self, mock_reverse):
        mock_reverse.return_value = Mock(data={'display_name': 'x'})
        response = self.client.get(
            '/api/places/reverse/', {'lat': 35.0, 'lon': 139.0}, HTTP_X_ADVENTURELOG_LOCALE='ja'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_reverse.call_args.kwargs['language'], 'ja')


class WikipediaSummaryLanguageTests(SimpleTestCase):
    def _host(self, tag):
        cache.clear()
        with patch('adventures.providers.wikipedia.requests.get') as mock_get:
            mock_get.return_value = _response({'type': 'disambiguation'})
            fetch_summary('Paris', language=tag)
        return mock_get.call_args.args[0]

    def test_region_tags_map_to_primary_wikipedia_host(self):
        self.assertTrue(self._host('en-US').startswith('https://en.wikipedia.org/'))
        self.assertTrue(self._host('pt-BR').startswith('https://pt.wikipedia.org/'))
        self.assertTrue(self._host('pt_BR').startswith('https://pt.wikipedia.org/'))
        self.assertTrue(self._host('zh-Hant').startswith('https://zh.wikipedia.org/'))


class QuickAddLanguageTests(SimpleTestCase):
    @patch('adventures.services.quick_add.get_place_details')
    def test_extract_google_place_details_forwards_language(self, mock_details):
        mock_details.return_value = {'description': 'A place'}

        place_id, details = extract_google_place_details({'place_id': 'abc'}, fallback_query='Tokyo', language='ja')

        self.assertEqual(place_id, 'abc')
        self.assertEqual(details, {'description': 'A place'})
        mock_details.assert_called_once_with('abc', fallback_query='Tokyo', language='ja')
