from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from adventures.providers.base import ProviderResult
from adventures.providers.geocoding.osm import reverse_geocode
from adventures.providers.places.osm import search_places as osm_search_places
from adventures.services.places.search import (
    ProviderSearchResult,
    search_places as search_places_service,
)
from adventures.utils.language import resolve_request_language
from adventures.views.places_api_view import PlacesAPI


def _response(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class ResolveRequestLanguageTests(SimpleTestCase):
    def _request(self, path="/api/places/search/", **headers):
        return Request(APIRequestFactory().get(path, **headers))

    def test_query_param_wins(self):
        request = self._request(
            "/api/places/search/?language=de",
            HTTP_X_ADVENTURELOG_LOCALE="ja",
        )
        self.assertEqual(resolve_request_language(request), "de")

    def test_ui_locale_header(self):
        request = self._request(HTTP_X_ADVENTURELOG_LOCALE="pt-BR")
        self.assertEqual(resolve_request_language(request), "pt-BR")

    def test_locale_cookie_for_direct_clients(self):
        request = self._request(HTTP_COOKIE="locale=ja")
        self.assertEqual(resolve_request_language(request), "ja")

    def test_accept_language_uses_first_entry(self):
        request = self._request(HTTP_ACCEPT_LANGUAGE="fr-CA,fr;q=0.9,en;q=0.8")
        self.assertEqual(resolve_request_language(request), "fr-CA")

    @override_settings(LANGUAGE_CODE="en-us")
    def test_invalid_values_fall_back_to_language_code(self):
        request = self._request(
            HTTP_X_ADVENTURELOG_LOCALE="bad header",
            HTTP_ACCEPT_LANGUAGE="*",
        )
        self.assertEqual(resolve_request_language(request), "en-us")


class OSMProviderLanguageTests(SimpleTestCase):
    @patch("adventures.providers.places.osm.requests.get")
    def test_places_sends_accept_language(self, mock_get):
        mock_get.return_value = _response([])

        osm_search_places("Tokyo", language="ja")

        self.assertEqual(mock_get.call_args.kwargs["headers"]["Accept-Language"], "ja")

    @patch("adventures.providers.places.osm.requests.get")
    def test_places_omits_accept_language_by_default(self, mock_get):
        mock_get.return_value = _response([])

        osm_search_places("Tokyo")

        self.assertNotIn("Accept-Language", mock_get.call_args.kwargs["headers"])

    @patch(
        "adventures.providers.geocoding.osm._is_host_resolvable",
        return_value=True,
    )
    @patch("adventures.providers.geocoding.osm.requests.get")
    def test_reverse_geocode_sends_accept_language(self, mock_get, _mock_resolvable):
        mock_get.return_value = _response({})

        reverse_geocode(35.0, 139.0, language="ja")

        self.assertEqual(mock_get.call_args.kwargs["headers"]["Accept-Language"], "ja")


class ServiceLanguageTests(SimpleTestCase):
    @override_settings(GOOGLE_MAPS_API_KEY="")
    @patch("adventures.services.places.search.osm_search")
    def test_search_passes_language_to_osm(self, mock_osm):
        mock_osm.return_value = ProviderResult(data=[])

        search_places_service("Tokyo", language="ja")

        mock_osm.assert_called_once_with("Tokyo", limit=20, language="ja")


class PlacesAPIViewLanguageTests(SimpleTestCase):
    @patch("adventures.views.places_api_view.search_places")
    def test_search_forwards_ui_locale(self, mock_search):
        mock_search.return_value = ProviderSearchResult(provider_used="osm", results=[])
        request = APIRequestFactory().get(
            "/api/places/search/",
            {"query": "Tokyo"},
            HTTP_X_ADVENTURELOG_LOCALE="ja",
        )
        force_authenticate(request, user=Mock())

        response = PlacesAPI.as_view({"get": "search"})(request)

        self.assertEqual(response.status_code, 200)
        mock_search.assert_called_once_with("Tokyo", language="ja")
