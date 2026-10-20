from unittest.mock import patch

from rest_framework.test import APITestCase

from integrations.models import ImmichIntegration
from users.models import CustomUser


class ImmichIntegrationApiTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='immich-api-user', email='immich-api-user@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

    def _create_integration(self):
        return ImmichIntegration.objects.create(
            user=self.user, server_url='http://immich.example.com/api', api_key='secret-immich-key'
        )

    def test_list_does_not_return_api_key(self):
        self._create_integration()

        response = self.client.get('/api/integrations/immich/')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('api_key', response.json())
        self.assertNotIn('secret-immich-key', response.content.decode())
        self.assertEqual(response.json()['server_url'], 'http://immich.example.com/api')

    @patch(
        'integrations.views.immich.ImmichIntegrationViewSet._validate_immich_connection',
        return_value=(True, 'http://immich.example.com/api', None),
    )
    def test_create_stores_key_but_does_not_echo_it(self, _validate):
        response = self.client.post(
            '/api/integrations/immich/',
            {'server_url': 'http://immich.example.com', 'api_key': 'brand-new-key', 'copy_locally': True},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn('api_key', response.json())
        self.assertNotIn('brand-new-key', response.content.decode())
        self.assertEqual(ImmichIntegration.objects.get(user=self.user).api_key, 'brand-new-key')

    @patch(
        'integrations.views.immich.ImmichIntegrationViewSet._validate_immich_connection',
        return_value=(True, 'http://immich.example.com/api', None),
    )
    def test_update_with_new_key_replaces_it_without_echoing(self, _validate):
        integration = self._create_integration()

        response = self.client.put(
            f'/api/integrations/immich/{integration.id}/',
            {'server_url': 'http://immich.example.com/api', 'api_key': 'rotated-key'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('api_key', response.json())
        integration.refresh_from_db()
        self.assertEqual(integration.api_key, 'rotated-key')
