"""The Immich server is an address the user typed, so it is checked when saved and again each time it is called."""

import socket
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from integrations.models import ImmichIntegration
from integrations.views.immich import ImmichViewSet

User = get_user_model()
LAN = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.50', 0))]
METADATA = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('169.254.169.254', 0))]


class ValidateImmichConnectionTests(TestCase):
    def validate(self, url):
        return ImmichViewSet()._validate_immich_connection(url, 'key')

    def test_credentials_are_refused_without_calling_the_server(self):
        with patch('integrations.views.immich.immich_get') as get:
            valid, _, message = self.validate('https://user:pass@immich.example.com')
        self.assertFalse(valid)
        self.assertIn('username or password', message)
        get.assert_not_called()

    def test_metadata_addresses_are_refused_without_calling_the_server(self):
        with patch('integrations.views.immich.immich_get') as get:
            for url in ('http://169.254.169.254', 'http://metadata.google.internal'):
                with self.subTest(url=url):
                    valid, _, message = self.validate(url)
                    self.assertFalse(valid)
                    self.assertEqual(message, 'Server URL host is not allowed.')
        get.assert_not_called()

    def test_a_name_that_resolves_to_a_metadata_address_is_refused(self):
        with patch('socket.getaddrinfo', return_value=METADATA), patch('integrations.views.immich.immich_get') as get:
            valid, _, message = self.validate('https://innocent.example.com')
        self.assertFalse(valid)
        self.assertEqual(message, 'Server URL host is not allowed.')
        get.assert_not_called()

    def test_a_lan_server_is_still_accepted(self):
        user = {'id': 'u', 'email': 'a@b.c', 'name': 'N', 'isAdmin': False, 'createdAt': 'x'}
        response = MagicMock(status_code=200)
        response.json.return_value = user
        with patch('socket.getaddrinfo', return_value=LAN), patch('integrations.views.immich.immich_get', return_value=response):
            valid, corrected, message = self.validate('http://immich.lan:2283')
        self.assertTrue(valid, message)
        self.assertEqual(corrected, 'http://immich.lan:2283')


class ImmichRequestGuardTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='immich-guard', password='test-pass')
        self.integration = ImmichIntegration.objects.create(
            user=self.user, server_url='http://immich.lan', api_key='key'
        )

    def albums(self):
        request = self.factory.get('/api/integrations/immich/albums/')
        force_authenticate(request, user=self.user)
        return ImmichViewSet.as_view({'get': 'albums'})(request)

    def test_a_stored_server_that_now_resolves_to_a_metadata_address_is_reported_unreachable(self):
        with patch('socket.getaddrinfo', return_value=METADATA), patch('core.net.create_connection') as connect:
            response = self.albums()
        self.assertIn(response.status_code, (400, 503))
        self.assertEqual(response.data['code'], 'immich.server_down')
        connect.assert_not_called()

    def test_the_request_goes_to_the_address_that_was_checked(self):
        with patch('socket.getaddrinfo', return_value=LAN), \
                patch('core.net.create_connection', side_effect=OSError('stop here')) as connect:
            response = self.albums()
        self.assertEqual(response.data['code'], 'immich.server_down')
        self.assertEqual(connect.call_args.args[0], ('192.168.1.50', 80))
