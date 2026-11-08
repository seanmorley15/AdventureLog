from unittest.mock import MagicMock, patch

import requests
from django.test import override_settings
from rest_framework.test import APITestCase

from adventures.services.places.photos import (
    PhotoError,
    fetch_google_photo,
    parse_proxy_photo_url,
    proxy_photo_url,
)
from core.testing import make_user

KEY = 'SECRET-KEY-123'
NAME = 'places/abc/photos/def'
GET = 'adventures.services.places.photos.requests.get'
DOWNLOAD = 'adventures.services.places.photos.download_remote_image'
IMAGE = {'content': b'\xff\xd8jpeg', 'content_type': 'image/jpeg', 'filename': 'x.jpg', 'source_url': 'u'}


def response(status=200, json=None, headers=None, redirect=False):
    r = MagicMock(status_code=status, headers=headers or {}, is_redirect=redirect)
    r.json.return_value = json or {}
    r.raise_for_status.side_effect = requests.exceptions.HTTPError('boom') if status >= 400 else None
    return r


class ProxyUrlTests(APITestCase):
    def test_round_trip(self):
        self.assertEqual(parse_proxy_photo_url(proxy_photo_url(name=NAME, size=400)), (NAME, None, 400))
        self.assertEqual(parse_proxy_photo_url(proxy_photo_url(reference='AbC_-1')), (None, 'AbC_-1', 800))

    def test_rejects_anything_that_is_not_ours(self):
        for value in (
            'https://evil.test/api/places/photo/?name=places/a/photos/b',
            '//evil.test/api/places/photo/?name=places/a/photos/b',
            '/api/other/?name=places/a/photos/b',
            '/api/places/photo/?name=../../etc/passwd',
            '/api/places/photo/?name=places/a/photos/b&reference=x',
            '/api/places/photo/?size=800',
            '/api/places/photo/?reference=x&size=99999',
            '/api/places/photo/?reference=x&size=abc',
            '',
        ):
            self.assertIsNone(parse_proxy_photo_url(value), value)


@override_settings(GOOGLE_MAPS_API_KEY=KEY)
class FetchGooglePhotoTests(APITestCase):
    @patch(DOWNLOAD, return_value=IMAGE)
    @patch(GET, return_value=response(json={'photoUri': 'https://lh3.googleusercontent.com/p'}))
    def test_v1_sends_key_in_header_only(self, get, download):
        self.assertEqual(fetch_google_photo(name=NAME, size=400), IMAGE)
        args, kwargs = get.call_args
        self.assertNotIn(KEY, args[0])
        self.assertNotIn(KEY, str(kwargs['params']))
        self.assertEqual(kwargs['headers'], {'X-Goog-Api-Key': KEY})
        self.assertEqual(download.call_args.args[0], 'https://lh3.googleusercontent.com/p')

    @patch(DOWNLOAD, return_value=IMAGE)
    @patch(GET, return_value=response(302, headers={'Location': 'https://lh3.googleusercontent.com/q'}, redirect=True))
    def test_legacy_does_not_follow_the_redirect_with_the_key(self, get, download):
        fetch_google_photo(reference='ref')
        self.assertFalse(get.call_args.kwargs['allow_redirects'])
        self.assertNotIn(KEY, download.call_args.args[0])

    @override_settings(GOOGLE_MAPS_API_KEY='')
    def test_not_configured(self):
        with self.assertRaises(PhotoError) as ctx:
            fetch_google_photo(name=NAME)
        self.assertEqual((ctx.exception.code, ctx.exception.status), ('not_configured', 503))

    @patch(GET, side_effect=requests.exceptions.ConnectionError(f'failed for url ?key={KEY}'))
    def test_errors_never_carry_the_key(self, get):
        with self.assertRaises(PhotoError) as ctx:
            fetch_google_photo(name=NAME)
        self.assertNotIn(KEY, str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)
        self.assertEqual(ctx.exception.status, 502)

    @patch(GET, side_effect=requests.exceptions.Timeout())
    def test_timeout(self, get):
        with self.assertRaises(PhotoError) as ctx:
            fetch_google_photo(name=NAME)
        self.assertEqual(ctx.exception.status, 504)

    @patch(GET, return_value=response(404))
    def test_missing_photo(self, get):
        with self.assertRaises(PhotoError) as ctx:
            fetch_google_photo(name=NAME)
        self.assertEqual(ctx.exception.status, 404)

    @patch(DOWNLOAD, return_value={**IMAGE, 'content_type': 'image/svg+xml'})
    @patch(GET, return_value=response(json={'photoUri': 'https://lh3.googleusercontent.com/p'}))
    def test_svg_is_refused(self, get, download):
        with self.assertRaises(PhotoError):
            fetch_google_photo(name=NAME)


@override_settings(GOOGLE_MAPS_API_KEY=KEY)
class PhotoViewTests(APITestCase):
    URL = '/api/places/photo/'
    FETCH = 'adventures.views.places.fetch_google_photo'

    def test_requires_login(self):
        self.assertIn(self.client.get(self.URL, {'name': NAME}).status_code, (401, 403))

    def test_validation(self):
        self.client.force_authenticate(make_user('photo-user', password='pw-12345678'))
        for params in ({}, {'name': NAME, 'reference': 'x'}, {'name': 'https://evil.test/x'}, {'reference': 'x', 'size': 5000}):
            self.assertEqual(self.client.get(self.URL, params).status_code, 400, params)

    @patch(FETCH, return_value=IMAGE)
    def test_serves_the_image_with_safe_headers(self, fetch):
        self.client.force_authenticate(make_user('photo-user2', password='pw-12345678'))
        r = self.client.get(self.URL, {'name': NAME, 'size': 300})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'image/jpeg')
        # Google's terms do not allow caching its photos, in the browser either.
        self.assertEqual(r['Cache-Control'], 'private, no-store')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(fetch.call_args.kwargs, {'name': NAME, 'reference': None, 'size': 300})

    @patch(FETCH, side_effect=PhotoError('The photo could not be loaded.', 'upstream_error', 502))
    def test_upstream_failure(self, fetch):
        self.client.force_authenticate(make_user('photo-user3', password='pw-12345678'))
        r = self.client.get(self.URL, {'name': NAME})
        self.assertEqual(r.status_code, 502)
        self.assertNotIn(KEY, r.content.decode())


@override_settings(GOOGLE_MAPS_API_KEY=KEY)
class ImportPathTests(APITestCase):
    def test_import_resolves_app_photo_addresses_server_side(self):
        from adventures.services.images.fetch import download_remote_image

        with patch(GET, return_value=response(json={'photoUri': 'https://lh3.googleusercontent.com/p'})), \
                patch(DOWNLOAD, return_value=IMAGE):
            result = download_remote_image(proxy_photo_url(name=NAME))
        self.assertEqual(result['content'], IMAGE['content'])
        # A full, key-free address: `ContentImage.source_url` is a URLField.
        self.assertEqual(result['source_url'], f'https://places.googleapis.com/v1/{NAME}/media')
        self.assertNotIn(KEY, result['source_url'])

    def test_importing_app_photo_addresses_saves_a_valid_source_url(self):
        from adventures.models import ContentImage, Location
        from adventures.services.images.fetch import import_remote_images_for_object

        owner = make_user('photo-importer', password='pw-12345678')
        location = Location.objects.create(user=owner, name='Louvre')
        jpeg = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00' + bytes(range(1, 65)) +
            b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
            b'\xff\xc4\x00\x14\x00\x01' + b'\x00' * 15 + b'\x00'
            b'\xff\xc4\x00\x14\x10\x01' + b'\x00' * 15 + b'\x00'
            b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xd2\xcf \xff\xd9'
        )
        with patch(GET, return_value=response(json={'photoUri': 'https://lh3.googleusercontent.com/p'})), \
                patch(DOWNLOAD, return_value={**IMAGE, 'content': jpeg}):
            summary = import_remote_images_for_object(
                location, [proxy_photo_url(name=NAME)], explicit_source=ContentImage.Source.GOOGLE
            )

        self.assertEqual(summary['failed_count'], 0, summary['failed'])
        image = ContentImage.objects.get(object_id=location.id)
        self.assertEqual(image.source_url, f'https://places.googleapis.com/v1/{NAME}/media')

    def test_fetch_endpoint_accepts_app_photo_addresses_and_still_rejects_junk(self):
        self.client.force_authenticate(make_user('photo-user4', password='pw-12345678'))
        with patch('adventures.views.images.download_remote_image', return_value=IMAGE):
            ok = self.client.post('/api/images/fetch-from-url/', {'url': proxy_photo_url(name=NAME)}, format='json')
            bad = self.client.post('/api/images/fetch-from-url/', {'url': '/api/places/photo/?name=nope'}, format='json')
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(bad.status_code, 400)
