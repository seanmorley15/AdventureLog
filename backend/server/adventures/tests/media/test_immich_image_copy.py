"""
A collaborator adding a photo from their own Immich server to someone else's record.

The server is the user's own, so a LAN address is fine, but the request must never be dialled to
a cloud-metadata address (GHSA-xcjj-9xwq-x28x, GHSA-v37j-gqjg-r88j) however the name resolves at
the time, and the asset id must not be able to change the path that is requested.
"""

import socket
from unittest.mock import patch

from rest_framework.test import APITestCase

from adventures.models import Collection, ContentImage, Location
from integrations.models import ImmichIntegration
from users.models import CustomUser


def _addr_infos(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 0))]


class ImmichCopyForCollaboratorTests(APITestCase):
    def setUp(self):
        owner = CustomUser.objects.create_user(username='owner', email='owner@example.com', password='pw-12345678')
        self.editor = CustomUser.objects.create_user(username='editor', email='editor@example.com', password='pw-12345678')
        collection = Collection.objects.create(user=owner, name='Trip')
        collection.shared_with.add(self.editor)
        self.location = Location.objects.create(user=owner, name='Place')
        self.location.collections.add(collection)
        # Saved while the name still resolved somewhere harmless.
        ImmichIntegration.objects.create(user=self.editor, server_url='http://immich.example/api', api_key='k')
        self.client.force_authenticate(user=self.editor)

    def add(self, immich_id):
        return self.client.post(
            '/api/images/',
            {'content_type': 'location', 'object_id': str(self.location.id), 'immich_id': immich_id},
            format='json',
        )

    def test_metadata_address_is_never_dialled(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('169.254.169.254')), \
                patch('core.net.create_connection') as connect:
            response = self.add('0b6a2c2e-6b1e-4d5e-9d0a-2f6f0b6c1d11')

        connect.assert_not_called()
        self.assertEqual(response.status_code, 502, response.content)
        self.assertFalse(ContentImage.objects.exists())

    def test_lan_address_is_dialled(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('192.168.1.20')), \
                patch('core.net.create_connection', side_effect=OSError('stop here')) as connect:
            self.add('0b6a2c2e-6b1e-4d5e-9d0a-2f6f0b6c1d11')

        self.assertEqual(connect.call_args.args[0], ('192.168.1.20', 80))

    def test_asset_id_cannot_steer_the_request_path(self):
        with patch('core.net.create_connection') as connect:
            for immich_id in ('../users/me', 'a/b', 'a?x=1', 'a#b', 'x' * 65):
                with self.subTest(immich_id=immich_id):
                    self.assertEqual(self.add(immich_id).status_code, 400)
        connect.assert_not_called()
