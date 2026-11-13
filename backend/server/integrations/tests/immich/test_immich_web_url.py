from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from integrations.models import ImmichIntegration
from integrations.views.integration import immich_web_url
from users.models import CustomUser


class ImmichWebUrlTests(SimpleTestCase):
    def test_the_api_suffix_is_dropped(self):
        self.assertEqual(immich_web_url('https://photos.example.com/api'), 'https://photos.example.com')
        self.assertEqual(immich_web_url('https://photos.example.com/api/'), 'https://photos.example.com')

    def test_an_address_without_the_suffix_is_kept(self):
        self.assertEqual(immich_web_url('https://example.com/immich'), 'https://example.com/immich')
        self.assertEqual(immich_web_url('https://example.com/rapid'), 'https://example.com/rapid')


class IntegrationStatusImmichTests(APITestCase):
    """The integration status gives the Immich web app's address for map links (#1117)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='photographer', email='photographer@example.com', password='testpassword'
        )
        self.client.force_authenticate(self.user)

    def test_no_web_url_without_immich(self):
        immich = self.client.get('/api/integrations/').json()['immich']
        self.assertFalse(immich['exists'])
        self.assertIsNone(immich['web_url'])

    def test_the_web_url_is_the_saved_address_without_api(self):
        ImmichIntegration.objects.create(
            user=self.user, server_url='https://photos.example.com/api', api_key='secret'
        )
        immich = self.client.get('/api/integrations/').json()['immich']
        self.assertEqual(immich['web_url'], 'https://photos.example.com')
        self.assertNotIn('api_key', immich)
