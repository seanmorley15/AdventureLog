"""The Wanderer server is whatever address the user typed, so it gets the same care as any self-hosted server."""

import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from django.test import SimpleTestCase

from core.net import create_connection as real_create_connection
from integrations.errors import IntegrationError
from integrations.models import WandererIntegration
from integrations.services import wanderer

LAN = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.50', 0))]
METADATA = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('169.254.169.254', 0))]


class NormalizeServerUrlTests(SimpleTestCase):
    def reject(self, url):
        with self.assertRaises(IntegrationError) as ctx:
            wanderer.normalize_server_url(url)
        return ctx.exception.user_message

    def test_credentials_queries_and_fragments_are_refused(self):
        self.assertIn('username or password', self.reject('https://user:pass@wanderer.example'))
        self.assertIn('query', self.reject('https://wanderer.example?x=1'))
        self.assertIn('query', self.reject('https://wanderer.example#frag'))

    def test_a_non_http_or_missing_address_is_refused(self):
        self.assertIn('valid http or https', self.reject('ftp://wanderer.example'))
        self.assertIn('valid http or https', self.reject('wanderer.example'))
        self.assertIn('valid http or https', self.reject(''))

    def test_metadata_addresses_and_names_are_refused(self):
        self.assertEqual(self.reject('http://169.254.169.254'), 'Server URL host is not allowed.')
        self.assertEqual(self.reject('http://metadata.google.internal'), 'Server URL host is not allowed.')
        with patch('socket.getaddrinfo', return_value=METADATA):
            self.assertEqual(self.reject('http://looks-innocent.example'), 'Server URL host is not allowed.')

    def test_an_unresolvable_name_is_refused_with_the_service_name(self):
        with patch('socket.getaddrinfo', side_effect=socket.gaierror):
            self.assertEqual(self.reject('http://nope.invalid'), 'Could not resolve Wanderer server hostname.')

    def test_lan_and_loopback_servers_are_allowed(self):
        self.assertEqual(wanderer.normalize_server_url('http://127.0.0.1:3000/'), 'http://127.0.0.1:3000')
        with patch('socket.getaddrinfo', return_value=LAN):
            self.assertEqual(wanderer.normalize_server_url('https://wanderer.lan/'), 'https://wanderer.lan')

    def test_building_a_trail_link_needs_no_dns(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('must not resolve')):
            link = wanderer.build_wanderer_trail_view_url('https://wanderer.example/', 't1', 'ana', 'w.example')
        self.assertEqual(link, 'https://wanderer.example/trail/view/@ana@w.example/t1')

    def test_building_a_trail_link_still_refuses_a_credentialed_url(self):
        with self.assertRaises(IntegrationError):
            wanderer.build_wanderer_trail_view_url('https://user:pass@wanderer.example', 't1', 'ana', 'w.example')


class WandererRequestTests(SimpleTestCase):
    def integration(self, url='http://wanderer.lan'):
        return WandererIntegration(server_url=url, api_key='secret')

    def test_a_stored_server_that_now_resolves_to_the_metadata_address_is_never_contacted(self):
        with patch('socket.getaddrinfo', return_value=METADATA), patch('core.net.create_connection') as connect:
            with self.assertRaises(IntegrationError) as ctx:
                wanderer.make_wanderer_request(self.integration(), '/api/v1/trail')
        self.assertEqual(ctx.exception.user_message, 'Unable to communicate with Wanderer server.')
        connect.assert_not_called()

    def test_a_stored_url_with_credentials_is_refused_before_any_request(self):
        with patch('socket.getaddrinfo') as lookup:
            with self.assertRaises(IntegrationError):
                wanderer.make_wanderer_request(self.integration('http://user:pass@wanderer.lan'), '/x')
        lookup.assert_not_called()

    def test_a_request_to_a_lan_server_completes_with_the_api_key(self):
        seen = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                seen['auth'] = self.headers['Authorization']
                seen['path'] = self.path
                body = b'{"ok": true}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        real_getaddrinfo = socket.getaddrinfo

        def resolve(host, *args, **kwargs):
            return LAN if host == 'wanderer.lan' else real_getaddrinfo(host, *args, **kwargs)

        def dial_local(address, *args, **kwargs):
            return real_create_connection(('127.0.0.1', server.server_address[1]), *args, **kwargs)

        with patch('socket.getaddrinfo', side_effect=resolve), patch('core.net.create_connection', side_effect=dial_local):
            response = wanderer.make_wanderer_request(self.integration(), '/api/v1/trail', params={'perPage': 1})

        self.assertEqual(response.json(), {'ok': True})
        self.assertEqual(seen['auth'], 'Bearer secret')
        self.assertTrue(seen['path'].startswith('/api/v1/trail'))

    def test_connection_validation_refuses_a_bad_address_without_calling_out(self):
        with patch('socket.getaddrinfo') as lookup:
            with self.assertRaises(IntegrationError):
                wanderer.validate_wanderer_connection('https://user:pass@wanderer.lan', 'key')
        lookup.assert_not_called()
