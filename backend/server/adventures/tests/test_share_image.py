from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from PIL import Image as PILImage
import io

from adventures.models import Collection, Location
from adventures.services.share_image import (
    ASPECTS,
    build_collection_share_image,
    build_location_share_image,
    valid_aspect,
)

User = get_user_model()


class ShareImageServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='shareuser', password='testpass123')
        self.other = User.objects.create_user(username='otheruser', password='testpass123')

    def _png_size(self, png_bytes: bytes) -> tuple[int, int]:
        img = PILImage.open(io.BytesIO(png_bytes))
        return img.size

    def test_valid_aspect(self):
        self.assertTrue(valid_aspect('square'))
        self.assertTrue(valid_aspect('story'))
        self.assertTrue(valid_aspect('landscape'))
        self.assertFalse(valid_aspect('wide'))

    def test_build_collection_share_image_all_aspects(self):
        start = date.today() + timedelta(days=10)
        end = start + timedelta(days=3)
        collection = Collection.objects.create(
            user=self.user,
            name='Coastal Road Trip',
            start_date=start,
            end_date=end,
            is_public=True,
        )
        location = Location.objects.create(
            user=self.user,
            name='Beach Stop',
            location='Pacific Coast',
            is_public=True,
        )
        collection.locations.add(location)

        for aspect, (width, height) in ASPECTS.items():
            png = build_collection_share_image(
                collection, aspect, f'http://example.com/collections/{collection.id}'
            )
            self.assertTrue(png.startswith(b'\x89PNG'))
            self.assertEqual(self._png_size(png), (width, height))

    def test_build_location_share_image_all_aspects(self):
        location = Location.objects.create(
            user=self.user,
            name='Summit View',
            location='Rocky Mountains',
            rating=4.5,
            tags=['hiking', 'scenic'],
            is_public=True,
        )

        for aspect, (width, height) in ASPECTS.items():
            png = build_location_share_image(
                location, aspect, f'http://example.com/locations/{location.id}'
            )
            self.assertTrue(png.startswith(b'\x89PNG'))
            self.assertEqual(self._png_size(png), (width, height))

    def test_collection_share_image_without_hero_image(self):
        collection = Collection.objects.create(
            user=self.user,
            name='No Photo Trip',
            is_public=True,
        )
        png = build_collection_share_image(
            collection, 'square', f'http://example.com/collections/{collection.id}'
        )
        self.assertTrue(png.startswith(b'\x89PNG'))
        self.assertEqual(self._png_size(png), ASPECTS['square'])


class ShareImageApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='testpass123')
        self.other = User.objects.create_user(username='apiother', password='testpass123')
        self.client.login(username='apiuser', password='testpass123')

        self.public_collection = Collection.objects.create(
            user=self.user,
            name='Public Trip',
            is_public=True,
        )
        self.private_collection = Collection.objects.create(
            user=self.user,
            name='Private Trip',
            is_public=False,
        )
        self.public_location = Location.objects.create(
            user=self.user,
            name='Public Place',
            is_public=True,
        )
        self.private_location = Location.objects.create(
            user=self.user,
            name='Private Place',
            is_public=False,
        )

    def test_owner_can_fetch_private_collection_share_image(self):
        url = f'/api/collections/{self.private_collection.id}/share-image/square/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'image/png')
        self.assertTrue(res.content.startswith(b'\x89PNG'))

    def test_anonymous_can_fetch_public_collection_share_image(self):
        self.client.logout()
        url = f'/api/collections/{self.public_collection.id}/share-image/landscape/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'image/png')

    def test_anonymous_cannot_fetch_private_collection_share_image(self):
        self.client.logout()
        url = f'/api/collections/{self.private_collection.id}/share-image/square/'
        res = self.client.get(url)
        self.assertIn(res.status_code, (403, 404))

    def test_owner_can_fetch_private_location_share_image(self):
        url = f'/api/locations/{self.private_location.id}/share-image/story/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'image/png')

    def test_anonymous_can_fetch_public_location_share_image(self):
        self.client.logout()
        url = f'/api/locations/{self.public_location.id}/share-image/square/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'image/png')

    def test_anonymous_cannot_fetch_private_location_share_image(self):
        self.client.logout()
        url = f'/api/locations/{self.private_location.id}/share-image/square/'
        res = self.client.get(url)
        self.assertIn(res.status_code, (403, 404))

    def test_invalid_aspect_returns_400(self):
        url = f'/api/collections/{self.public_collection.id}/share-image/wide/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_download_disposition(self):
        url = (
            f'/api/collections/{self.public_collection.id}/share-image/square/?download=1'
        )
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn('attachment', res['Content-Disposition'])

    def test_shared_user_can_fetch_private_collection_share_image(self):
        self.private_collection.shared_with.add(self.other)
        self.client.logout()
        self.client.login(username='apiother', password='testpass123')
        url = f'/api/collections/{self.private_collection.id}/share-image/square/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'image/png')

    def test_anonymous_can_export_public_collection_pdf(self):
        self.client.logout()
        url = f'/api/collections/{self.public_collection.id}/export-pdf/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertTrue(res.content.startswith(b'%PDF'))

    def test_owner_can_export_private_collection_pdf(self):
        url = f'/api/collections/{self.private_collection.id}/export-pdf/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')

    def test_anonymous_cannot_export_private_collection_pdf(self):
        self.client.logout()
        url = f'/api/collections/{self.private_collection.id}/export-pdf/'
        res = self.client.get(url)
        self.assertIn(res.status_code, (403, 404))

    def test_shared_user_can_export_private_collection_pdf(self):
        self.private_collection.shared_with.add(self.other)
        self.client.logout()
        self.client.login(username='apiother', password='testpass123')
        url = f'/api/collections/{self.private_collection.id}/export-pdf/'
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
