from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from integrations.models import ImmichIntegration
from integrations.views.immich_view import ImmichIntegrationView

User = get_user_model()


class ImmichViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='immich-user', password='test-pass')
        self.integration = ImmichIntegration.objects.create(
            user=self.user,
            server_url='http://immich.example.com/api',
            api_key='test-api-key',
        )
        self.view = ImmichIntegrationView.as_view({'get': 'search'})
        self.album_view = ImmichIntegrationView.as_view({'get': 'album'})

    @patch('integrations.views.immich_view.requests.post')
    def test_search_by_date_uses_iso8601_datetime_range(self, mock_post):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'assets': {
                'items': [{'id': 'asset-1'}],
            }
        }
        mock_post.return_value = mock_response

        request = self.factory.get('/api/integrations/immich/search/', {'date': '2024-06-15'})
        force_authenticate(request, user=self.user)

        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['takenAfter'], '2024-06-15T00:00:00.000Z')
        self.assertEqual(kwargs['json']['takenBefore'], '2024-06-16T00:00:00.000Z')

    @patch('integrations.views.immich_view.requests.get')
    @patch('integrations.views.immich_view.requests.post')
    def test_album_falls_back_to_metadata_search_without_inline_assets(self, mock_post, mock_get):
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            'id': 'album-1',
            'albumName': 'Trip Photos',
        }
        mock_get.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.ok = True
        mock_post_response.json.return_value = {
            'assets': {
                'items': [{'id': 'asset-1'}, {'id': 'asset-2'}],
            }
        }
        mock_post.return_value = mock_post_response

        request = self.factory.get('/api/integrations/immich/albums/album-1/')
        force_authenticate(request, user=self.user)

        response = self.album_view(request, albumid='album-1')

        self.assertEqual(response.status_code, 200)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['albumIds'], ['album-1'])
        self.assertEqual(len(response.data['results']), 2)

    @patch('integrations.views.immich_view.requests.get')
    def test_album_uses_inline_assets_when_available(self, mock_get):
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            'id': 'album-1',
            'albumName': 'Trip Photos',
            'assets': [{'id': 'asset-legacy-1'}],
        }
        mock_get.return_value = mock_get_response

        request = self.factory.get('/api/integrations/immich/albums/album-1/')
        force_authenticate(request, user=self.user)

        with patch('integrations.views.immich_view.requests.post') as mock_post:
            response = self.album_view(request, albumid='album-1')

        self.assertEqual(response.status_code, 200)
        mock_post.assert_not_called()
        self.assertEqual(len(response.data['results']), 1)
