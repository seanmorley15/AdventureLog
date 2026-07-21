from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from adventures.models import ContentImage, Location
from adventures.serializers import ContentImageSerializer
from adventures.services.images.metadata import (
    ImageSource,
    create_content_image,
    extract_gps_from_bytes,
    infer_source_from_url,
    resolve_image_metadata,
    _dms_to_decimal,
)
from adventures.utils.geo import make_point, point_to_lat_lon
from users.models import CustomUser


class ImageSourceInferenceTests(TestCase):
    def test_google_url(self):
        self.assertEqual(
            infer_source_from_url(
                'https://places.googleapis.com/v1/photo/media?key=test'
            ),
            ImageSource.GOOGLE,
        )

    def test_wikipedia_url(self):
        self.assertEqual(
            infer_source_from_url('https://upload.wikimedia.org/wikipedia/commons/a/a1/test.jpg'),
            ImageSource.WIKIPEDIA,
        )

    def test_generic_url(self):
        self.assertEqual(
            infer_source_from_url('https://example.com/photo.jpg'),
            ImageSource.URL,
        )

    def test_spoofed_hostnames_are_not_matched(self):
        spoofed_urls = [
            'https://evil.googleapis.com.attacker.com/photo.jpg',
            'https://notgoogleusercontent.com/photo.jpg',
            'https://evil.wikimedia.org.attacker.com/photo.jpg',
            'https://notwikipedia.org/photo.jpg',
        ]
        for url in spoofed_urls:
            with self.subTest(url=url):
                self.assertEqual(infer_source_from_url(url), ImageSource.URL)


class ImageMetadataResolutionTests(TestCase):
    def test_explicit_source_overrides_url_inference(self):
        metadata = resolve_image_metadata(
            source_url='https://upload.wikimedia.org/wikipedia/commons/x.jpg',
            explicit_source=ImageSource.GOOGLE,
        )
        self.assertEqual(metadata['source'], ImageSource.GOOGLE)

    def test_immich_id_sets_immich_source(self):
        metadata = resolve_image_metadata(immich_id='abc-123')
        self.assertEqual(metadata['source'], ImageSource.IMMICH)

    def test_extract_gps_returns_none_for_non_gps_image(self):
        from PIL import Image
        import io

        buffer = io.BytesIO()
        Image.new('RGB', (4, 4), color='blue').save(buffer, format='JPEG')
        self.assertIsNone(extract_gps_from_bytes(buffer.getvalue()))

    @patch('adventures.services.images.metadata.fetch_immich_coordinates')
    def test_resolve_metadata_falls_back_to_immich_when_file_has_no_gps(
        self, mock_fetch_immich_coordinates
    ):
        from PIL import Image
        import io

        buffer = io.BytesIO()
        Image.new('RGB', (4, 4), color='blue').save(buffer, format='JPEG')
        file_bytes = buffer.getvalue()
        immich_point = make_point(-70.6473, 44.9673)
        mock_fetch_immich_coordinates.return_value = immich_point
        mock_integration = object()

        metadata = resolve_image_metadata(
            file_bytes=file_bytes,
            immich_id='abc-123',
            immich_integration=mock_integration,
        )

        self.assertEqual(metadata['source'], ImageSource.IMMICH)
        self.assertEqual(metadata['coordinates'], immich_point)
        mock_fetch_immich_coordinates.assert_called_once_with(mock_integration, 'abc-123')


class DmsConversionTests(TestCase):
    def test_ifdrational_components(self):
        from PIL.TiffImagePlugin import IFDRational

        values = (IFDRational(44, 1), IFDRational(58, 2), IFDRational(1234, 100))
        result = _dms_to_decimal(values, 'N')
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 44.486761111111115, places=4)

    def test_tuple_rational_components(self):
        values = ((44, 1), (58, 2), (1234, 100))
        result = _dms_to_decimal(values, 'N')
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 44.486761111111115, places=4)

    def test_bytes_ref_applies_hemisphere(self):
        values = ((44, 1), (58, 1), (0, 1))
        north = _dms_to_decimal(values, b'N')
        south = _dms_to_decimal(values, b'S')
        self.assertAlmostEqual(north, 44.96666666666667, places=4)
        self.assertAlmostEqual(south, -44.96666666666667, places=4)

    def test_extract_gps_from_jpeg_with_exif(self):
        from PIL import Image
        import io

        try:
            import piexif
        except ImportError:
            self.skipTest('piexif is not installed')

        lat, lon = 44.9673, -70.6473

        def to_deg(value, refs):
            abs_value = abs(value)
            deg = int(abs_value)
            t1 = (abs_value - deg) * 60
            min_ = int(t1)
            sec = round((t1 - min_) * 60 * 100)
            return ((deg, 1), (min_, 1), (sec, 100)), refs[0 if value < 0 else 1]

        lat_deg = to_deg(lat, ['S', 'N'])
        lon_deg = to_deg(lon, ['W', 'E'])
        exif_dict = {
            'GPS': {
                piexif.GPSIFD.GPSLatitudeRef: lat_deg[1],
                piexif.GPSIFD.GPSLatitude: lat_deg[0],
                piexif.GPSIFD.GPSLongitudeRef: lon_deg[1],
                piexif.GPSIFD.GPSLongitude: lon_deg[0],
            }
        }
        exif_bytes = piexif.dump(exif_dict)
        buffer = io.BytesIO()
        Image.new('RGB', (4, 4), color='blue').save(buffer, format='JPEG', exif=exif_bytes)

        point = extract_gps_from_bytes(buffer.getvalue())
        self.assertIsNotNone(point)
        extracted_lat, extracted_lon = point_to_lat_lon(point)
        self.assertAlmostEqual(extracted_lat, lat, places=3)
        self.assertAlmostEqual(extracted_lon, lon, places=3)


class CreateContentImageTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='image-user',
            email='image-user@example.com',
            password='testpassword123',
        )
        self.location = Location.objects.create(user=self.user, name='Test Location')
        self.content_type = ContentType.objects.get_for_model(Location)

    def test_create_with_explicit_google_source(self):
        from django.core.files.base import ContentFile
        from PIL import Image
        import io

        buffer = io.BytesIO()
        Image.new('RGB', (4, 4), color='red').save(buffer, format='JPEG')
        file_bytes = buffer.getvalue()

        image = create_content_image(
            user=self.user,
            content_type=self.content_type,
            object_id=str(self.location.id),
            image_file=ContentFile(file_bytes, name='test.jpg'),
            file_bytes=file_bytes,
            explicit_source=ImageSource.GOOGLE,
            source_url='https://places.googleapis.com/v1/photo/media',
        )
        image.refresh_from_db()
        self.assertEqual(image.source, ImageSource.GOOGLE)
        self.assertEqual(image.source_url, 'https://places.googleapis.com/v1/photo/media')

    def test_create_with_coordinates(self):
        from django.core.files.base import ContentFile
        from PIL import Image
        import io

        buffer = io.BytesIO()
        Image.new('RGB', (4, 4), color='red').save(buffer, format='JPEG')
        file_bytes = buffer.getvalue()
        point = make_point(2.3522, 48.8566)
        image = create_content_image(
            user=self.user,
            content_type=self.content_type,
            object_id=str(self.location.id),
            image_file=ContentFile(file_bytes, name='test.jpg'),
            file_bytes=file_bytes,
            coordinates=point,
        )
        image.refresh_from_db()
        lat, lon = point_to_lat_lon(image.coordinates)
        self.assertAlmostEqual(lat, 48.8566, places=4)
        self.assertAlmostEqual(lon, 2.3522, places=4)


class ContentImageSerializerMetadataTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='serializer-user',
            email='serializer-user@example.com',
            password='testpassword123',
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')
        self.request.user = self.user

    def test_serializer_exposes_source_and_coordinates(self):
        from django.core.files.base import ContentFile
        from PIL import Image
        import io

        buffer = io.BytesIO()
        Image.new('RGB', (4, 4), color='red').save(buffer, format='JPEG')

        image = ContentImage.objects.create(
            user=self.user,
            content_type=ContentType.objects.get_for_model(Location),
            object_id='00000000-0000-0000-0000-000000000001',
            image=ContentFile(buffer.getvalue(), name='test.jpg'),
            source=ContentImage.Source.WIKIPEDIA,
            source_url='https://upload.wikimedia.org/wikipedia/commons/test.jpg',
            coordinates=make_point(-73.968285, 40.785091),
        )
        data = ContentImageSerializer(image, context={'request': self.request}).data
        self.assertIsNotNone(data)
        self.assertEqual(data['source'], ContentImage.Source.WIKIPEDIA)
        self.assertEqual(data['source_url'], 'https://upload.wikimedia.org/wikipedia/commons/test.jpg')
        self.assertAlmostEqual(data['latitude'], 40.785091, places=4)
        self.assertAlmostEqual(data['longitude'], -73.968285, places=4)


class ImageMapPinSerializerTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='pin-user',
            email='pin-user@example.com',
            password='testpassword123',
        )

    def test_map_pin_serializer_includes_parent_fields(self):
        from django.core.files.base import ContentFile
        from PIL import Image
        import io

        location = Location.objects.create(
            user=self.user,
            name='GPS Place',
            coordinates=make_point(2.0, 48.0),
        )
        buffer = io.BytesIO()
        Image.new('RGB', (4, 4), color='blue').save(buffer, format='JPEG')

        image = ContentImage.objects.create(
            user=self.user,
            content_type=ContentType.objects.get_for_model(Location),
            object_id=str(location.id),
            image=ContentFile(buffer.getvalue(), name='gps.jpg'),
            coordinates=make_point(-122.4194, 37.7749),
            source=ContentImage.Source.UPLOAD,
        )

        from adventures.serializers import ImageMapPinSerializer

        data = ImageMapPinSerializer(image).data
        self.assertIsNotNone(data)
        self.assertEqual(data['parent_type'], 'location')
        self.assertEqual(data['parent_id'], str(location.id))
        self.assertEqual(data['parent_name'], 'GPS Place')
        self.assertAlmostEqual(data['latitude'], 37.7749, places=4)
        self.assertAlmostEqual(data['longitude'], -122.4194, places=4)
