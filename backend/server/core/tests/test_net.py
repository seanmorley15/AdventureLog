"""Pins the outbound-host policies that use DNS resolution.

These are deliberately different policies, so each is tested on its own:

* image import (user-supplied URL)  - public internet only, ports 80/443
* Endurain server URL               - LAN allowed, metadata/link-local/multicast blocked
* OSM geocoder                      - DNS reachability probe for a fixed host
"""

import requests
import socket
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import SimpleTestCase

from adventures.providers.geocoding import osm
from adventures.services.images.fetch import download_remote_image
from integrations.errors import IntegrationError
from integrations.services.endurain import normalize_server_url

PUBLIC_IP = '93.184.216.34'


def _addr_infos(*ips):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 0)) for ip in ips]


class _Reached(Exception):
    """Raised by the patched requests.get to prove the guard let the URL through."""


class ImageImportHostPolicyTests(SimpleTestCase):
    def _blocked(self, url):
        with patch('requests.Session.get', side_effect=AssertionError('must not fetch')):
            with self.assertRaises(ValueError) as ctx:
                download_remote_image(url)
        return str(ctx.exception)

    def test_scheme_must_be_http_or_https(self):
        self.assertEqual(
            self._blocked('ftp://example.com/a.jpg'),
            'Invalid URL scheme. Only http and https are allowed.',
        )

    def test_non_standard_ports_are_blocked(self):
        self.assertEqual(
            self._blocked(f'http://{PUBLIC_IP}:8080/a.jpg'),
            'Non-standard ports are not allowed.',
        )

    def test_missing_hostname_is_blocked(self):
        self.assertEqual(self._blocked('http:///a.jpg'), 'Invalid URL: missing hostname.')

    def test_unresolvable_hostname_is_blocked(self):
        with patch('socket.getaddrinfo', side_effect=socket.gaierror):
            self.assertEqual(self._blocked('http://nope.invalid/a.jpg'), 'Could not resolve hostname.')

    def test_empty_resolution_is_blocked(self):
        with patch('socket.getaddrinfo', return_value=[]):
            self.assertEqual(self._blocked('http://nope.invalid/a.jpg'), 'Could not resolve hostname.')

    def test_garbage_resolved_address_is_blocked(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('not-an-ip')):
            self.assertEqual(
                self._blocked('http://weird.example/a.jpg'),
                'Invalid IP address resolved from hostname.',
            )

    def test_internal_addresses_are_blocked(self):
        for ip in ('127.0.0.1', '10.0.0.5', '192.168.1.1', '169.254.169.254',
                   '224.0.0.1', '240.0.0.1', '::1', 'fc00::1', 'fe80::1'):
            host = f'[{ip}]' if ':' in ip else ip
            with self.subTest(ip=ip):
                self.assertEqual(
                    self._blocked(f'http://{host}/a.jpg'),
                    'Access to internal networks is not allowed.',
                )

    def test_hostname_resolving_to_internal_address_is_blocked(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('10.1.2.3')):
            self.assertEqual(
                self._blocked('http://rebind.example/a.jpg'),
                'Access to internal networks is not allowed.',
            )

    def test_any_internal_address_among_several_blocks(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos(PUBLIC_IP, '127.0.0.1')):
            self.assertEqual(
                self._blocked('http://mixed.example/a.jpg'),
                'Access to internal networks is not allowed.',
            )

    def test_public_address_reaches_the_request(self):
        with patch('requests.Session.get', side_effect=_Reached):
            with self.assertRaises(_Reached):
                download_remote_image(f'http://{PUBLIC_IP}/a.jpg')

    def test_redirect_to_internal_address_is_blocked(self):
        redirect = MagicMock(is_redirect=True, headers={'Location': 'http://127.0.0.1/secret.jpg'})
        with patch('requests.Session.get', return_value=redirect):
            with self.assertRaises(ValueError) as ctx:
                download_remote_image(f'http://{PUBLIC_IP}/a.jpg')
        self.assertEqual(
            str(ctx.exception),
            'Redirect blocked: Access to internal networks is not allowed.',
        )


class EndurainServerUrlPolicyTests(SimpleTestCase):
    def _rejected(self, url):
        with self.assertRaises(IntegrationError) as ctx:
            normalize_server_url(url)
        self.assertEqual(ctx.exception.code, 'endurain.invalid_server_url')
        return ctx.exception.user_message

    def test_private_and_loopback_hosts_are_allowed_for_self_hosting(self):
        for url in ('http://127.0.0.1:8080', 'http://192.168.1.10', 'https://10.0.0.1/endurain'):
            with self.subTest(url=url):
                self.assertEqual(normalize_server_url(url), url)

    def test_hostname_resolving_to_private_address_is_allowed(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('192.168.1.50')):
            self.assertEqual(normalize_server_url('http://endurain.lan'), 'http://endurain.lan')

    def test_link_local_and_metadata_addresses_are_blocked(self):
        for url in ('http://169.254.169.254', 'http://169.254.0.1', 'http://[fd00:ec2::254]'):
            with self.subTest(url=url):
                self.assertEqual(self._rejected(url), 'Server URL host is not allowed.')

    def test_multicast_and_unspecified_addresses_are_blocked(self):
        for url in ('http://224.0.0.1', 'http://0.0.0.0'):
            with self.subTest(url=url):
                self.assertEqual(self._rejected(url), 'Server URL host is not allowed.')

    def test_metadata_hostnames_are_blocked_without_dns(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('must not resolve')):
            for url in ('http://metadata.google.internal', 'http://METADATA.GOOGLE.COM',
                        'http://instance-data', 'http://metadata.google.internal.',
                        'http://x.metadata.google.internal'):
                with self.subTest(url=url):
                    self.assertEqual(self._rejected(url), 'Server URL host is not allowed.')

    def test_hostname_resolving_to_metadata_address_is_blocked(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('169.254.169.254')):
            self.assertEqual(self._rejected('http://rebind.example'), 'Server URL host is not allowed.')

    def test_unresolvable_hostname_is_rejected(self):
        with patch('socket.getaddrinfo', side_effect=socket.gaierror):
            self.assertEqual(self._rejected('http://nope.invalid'), 'Could not resolve Endurain server hostname.')

    def test_empty_resolution_is_rejected(self):
        with patch('socket.getaddrinfo', return_value=[]):
            self.assertEqual(self._rejected('http://nope.invalid'), 'Could not resolve Endurain server hostname.')

    def test_garbage_resolved_address_is_rejected(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('not-an-ip')):
            self.assertEqual(self._rejected('http://weird.example'), 'Server URL resolved to an invalid IP address.')


class OsmReachabilityProbeTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_unresolvable_nominatim_returns_a_provider_error(self):
        with patch('socket.gethostbyname', side_effect=socket.gaierror), \
                patch('requests.Session.get', side_effect=AssertionError('must not fetch')):
            result = osm.reverse_geocode(10.1111, 20.2222)
        self.assertEqual(result.error, 'Unable to resolve OpenStreetMap service')

    def test_resolvable_nominatim_proceeds_to_the_request(self):
        response = MagicMock()
        response.json.return_value = {'display_name': 'Somewhere'}
        with patch('socket.gethostbyname', return_value='1.2.3.4'), \
                patch('requests.get', return_value=response) as get:
            result = osm.reverse_geocode(30.3333, 40.4444)
        get.assert_called_once()
        self.assertEqual(result.data, {'display_name': 'Somewhere'})


class PublicAddressTests(SimpleTestCase):
    """What counts as the public internet, for the image-import policy."""

    def blocked(self, ip):
        from core.net import is_public_ip
        import ipaddress

        return not is_public_ip(ipaddress.ip_address(ip))

    def test_carrier_grade_nat_and_other_special_ranges_are_not_public(self):
        for ip in ('100.64.0.1', '100.127.255.254', '192.0.0.8', '198.18.0.1', '192.0.2.1', '203.0.113.9'):
            with self.subTest(ip=ip):
                self.assertTrue(self.blocked(ip))

    def test_ipv4_addresses_hidden_in_ipv6_are_judged_as_ipv4(self):
        for ip in ('::ffff:127.0.0.1', '::ffff:10.0.0.5', '::ffff:169.254.169.254', '::ffff:100.64.0.1'):
            with self.subTest(ip=ip):
                self.assertTrue(self.blocked(ip))

    def test_ordinary_public_addresses_are_allowed(self):
        for ip in ('93.184.216.34', '8.8.8.8', '2606:2800:220:1:248:1893:25c8:1946'):
            with self.subTest(ip=ip):
                self.assertFalse(self.blocked(ip))

    def test_the_url_check_uses_the_same_rule(self):
        for ip in ('100.64.0.1', '[::ffff:127.0.0.1]'):
            with self.subTest(ip=ip):
                with patch('requests.Session.get', side_effect=AssertionError('must not fetch')):
                    with self.assertRaises(ValueError) as ctx:
                        download_remote_image(f'http://{ip}/a.jpg')
                self.assertEqual(str(ctx.exception), 'Access to internal networks is not allowed.')


class ConnectTimeAddressCheckTests(SimpleTestCase):
    """The address that was checked is the address that is connected to (no DNS rebinding)."""

    def fetch(self, url):
        from core.net import public_session

        with public_session() as session:
            return session.get(url, timeout=2)

    def test_a_name_that_resolves_to_an_internal_address_is_never_connected_to(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('127.0.0.1')), \
                patch('core.net.create_connection') as connect:
            with self.assertRaises(requests.exceptions.ConnectionError):
                self.fetch('http://rebind.example/a.jpg')
        connect.assert_not_called()

    def test_one_internal_address_among_several_refuses_the_whole_name(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos(PUBLIC_IP, '10.0.0.1')), \
                patch('core.net.create_connection') as connect:
            with self.assertRaises(requests.exceptions.ConnectionError):
                self.fetch('http://mixed.example/a.jpg')
        connect.assert_not_called()

    def test_the_connection_goes_to_the_checked_address_not_to_a_second_lookup(self):
        answers = iter([_addr_infos(PUBLIC_IP), _addr_infos('127.0.0.1')])
        with patch('socket.getaddrinfo', side_effect=lambda *a, **k: next(answers)) as lookup, \
                patch('core.net.create_connection', side_effect=OSError('stop here')) as connect:
            with self.assertRaises(requests.exceptions.ConnectionError):
                self.fetch('http://flip.example/a.jpg')

        self.assertEqual(lookup.call_count, 1)
        self.assertEqual(connect.call_args.args[0], (PUBLIC_IP, 80))

    def test_https_connects_to_the_checked_address_too(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos(PUBLIC_IP)), \
                patch('core.net.create_connection', side_effect=OSError('stop here')) as connect:
            with self.assertRaises(requests.exceptions.ConnectionError):
                self.fetch('https://secure.example/a.jpg')
        self.assertEqual(connect.call_args.args[0], (PUBLIC_IP, 443))

    def test_an_unresolvable_name_is_a_connection_error(self):
        with patch('socket.getaddrinfo', side_effect=socket.gaierror), patch('core.net.create_connection') as connect:
            with self.assertRaises(requests.exceptions.ConnectionError):
                self.fetch('http://nope.invalid/a.jpg')
        connect.assert_not_called()


class PublicSessionEndToEndTests(SimpleTestCase):
    """A real HTTP exchange through the pinned connection, with DNS and the dial step redirected to a local server."""

    def test_a_request_to_a_public_looking_name_completes(self):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        from core.net import create_connection as real_create_connection, public_session

        seen = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                seen['host'] = self.headers['Host']
                body = b'hello'
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        dialled = []

        def dial_local(address, *args, **kwargs):
            dialled.append(address)
            return real_create_connection(('127.0.0.1', server.server_address[1]), *args, **kwargs)

        real_getaddrinfo = socket.getaddrinfo

        def resolve(host, *args, **kwargs):
            if host == 'photos.example':
                return _addr_infos(PUBLIC_IP)
            return real_getaddrinfo(host, *args, **kwargs)

        with patch('socket.getaddrinfo', side_effect=resolve), \
                patch('core.net.create_connection', side_effect=dial_local):
            with public_session() as session:
                response = session.get('http://photos.example/pic.txt', timeout=5)

        self.assertEqual((response.status_code, response.content), (200, b'hello'))
        self.assertEqual(dialled, [(PUBLIC_IP, 80)])
        self.assertEqual(seen['host'], 'photos.example')


class SelfHostedAddressTests(SimpleTestCase):
    """Servers people run themselves may be on their LAN, but never on cloud-metadata or link-local addresses."""

    def allowed(self, ip):
        import ipaddress

        from core.net import is_self_hosted_ip

        return is_self_hosted_ip(ipaddress.ip_address(ip))

    def test_lan_and_loopback_addresses_are_allowed(self):
        for ip in ('127.0.0.1', '192.168.1.10', '10.0.0.5', '172.16.4.2', '::1', 'fd12:3456::1', '93.184.216.34'):
            with self.subTest(ip=ip):
                self.assertTrue(self.allowed(ip))

    def test_metadata_link_local_multicast_and_unspecified_addresses_are_refused(self):
        for ip in ('169.254.169.254', '169.254.0.1', 'fd00:ec2::254', 'fe80::1', '224.0.0.1', '0.0.0.0', '::',
                   '::ffff:169.254.169.254'):
            with self.subTest(ip=ip):
                self.assertFalse(self.allowed(ip))


class SelfHostedSessionTests(SimpleTestCase):
    def fetch(self, url):
        from core.net import self_hosted_session

        with self_hosted_session() as session:
            return session.get(url, timeout=2)

    def test_a_name_resolving_to_the_metadata_address_is_never_connected_to(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('169.254.169.254')), \
                patch('core.net.create_connection') as connect:
            with self.assertRaises(requests.exceptions.ConnectionError):
                self.fetch('http://immich.example/api')
        connect.assert_not_called()

    def test_a_name_resolving_to_a_lan_address_is_connected_to_at_that_address(self):
        with patch('socket.getaddrinfo', return_value=_addr_infos('192.168.1.50')), \
                patch('core.net.create_connection', side_effect=OSError('stop here')) as connect:
            with self.assertRaises(requests.exceptions.ConnectionError):
                self.fetch('http://immich.lan:2283/api')
        self.assertEqual(connect.call_args.args[0], ('192.168.1.50', 2283))

    def test_the_public_session_still_refuses_that_lan_address(self):
        from core.net import public_session

        with patch('socket.getaddrinfo', return_value=_addr_infos('192.168.1.50')), \
                patch('core.net.create_connection') as connect:
            with public_session() as session, self.assertRaises(requests.exceptions.ConnectionError):
                session.get('http://immich.lan/api', timeout=2)
        connect.assert_not_called()
