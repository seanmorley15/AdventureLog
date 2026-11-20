from django.test import SimpleTestCase, override_settings

from adventures.services.recommendations.parsers import normalize_price_level, parse_google_places, parse_overpass

ORIGIN = (48.85, 2.29)


class GoogleParserTests(SimpleTestCase):
    def place(self, **extra):
        base = {
            'id': 'abc',
            'displayName': {'text': 'Louvre'},
            'location': {'latitude': 48.86, 'longitude': 2.33},
            'types': ['museum'],
            'rating': 4.7,
            'userRatingCount': 1000,
            'businessStatus': 'OPERATIONAL',
            'priceLevel': 'PRICE_LEVEL_MODERATE',
            'photos': [{'name': 'places/abc/photos/1'}],
        }
        base.update(extra)
        return base

    @override_settings(GOOGLE_MAPS_API_KEY='k')
    def test_parses_v1_place(self):
        [r] = parse_google_places([self.place()], ORIGIN, 'culture')
        self.assertEqual(r['id'], 'google:abc')
        self.assertEqual(r['place_id'], 'abc')
        self.assertEqual(r['price_level'], 2)
        self.assertEqual(r['category'], 'culture')
        self.assertEqual(r['photos'], ['/api/places/photo/?name=places%2Fabc%2Fphotos%2F1&size=800'])
        self.assertGreater(r['distance_km'], 0)

    def test_drops_unusable_places(self):
        places = [
            self.place(id=None),
            self.place(displayName=None),
            self.place(location={}),
            self.place(businessStatus='CLOSED_PERMANENTLY'),
            self.place(rating=2.1, userRatingCount=50),
        ]
        self.assertEqual(parse_google_places(places, ORIGIN, 'culture'), [])

    def test_keeps_low_rated_place_with_few_reviews(self):
        self.assertEqual(len(parse_google_places([self.place(rating=2.5, userRatingCount=3)], ORIGIN, 'culture')), 1)

    @override_settings(GOOGLE_MAPS_API_KEY='k')
    def test_legacy_photo_reference_and_int_price(self):
        [r] = parse_google_places([self.place(priceLevel=3, photos=[{'photo_reference': 'ref'}])], ORIGIN, 'food')
        self.assertEqual(r['price_level'], 3)
        self.assertEqual(r['photos'], ['/api/places/photo/?reference=ref&size=800'])

    def test_price_level_normalization(self):
        self.assertEqual(normalize_price_level('PRICE_LEVEL_FREE'), 0)
        self.assertIsNone(normalize_price_level('nonsense'))
        self.assertIsNone(normalize_price_level(None))


class OverpassParserTests(SimpleTestCase):
    def test_node_way_and_relation(self):
        data = {
            'elements': [
                {'type': 'node', 'id': 1, 'lat': 48.0, 'lon': 2.0, 'tags': {'name': 'A', 'tourism': 'museum', 'wikidata': 'Q1'}},
                {'type': 'way', 'id': 2, 'center': {'lat': 0.0, 'lon': 0.0}, 'tags': {'name': 'B', 'leisure': 'park'}},
                {'type': 'relation', 'id': 3, 'center': {'lat': 1, 'lon': 1}, 'tags': {'official_name': 'C', 'amenity': 'cafe'}},
            ]
        }
        results = parse_overpass(data, ORIGIN, 'culture')
        self.assertEqual([r['id'] for r in results], ['osm:node:1', 'osm:way:2', 'osm:relation:3'])
        self.assertTrue(results[0]['is_verified'])
        # A way centered on 0,0 keeps its coordinates instead of being dropped as falsy.
        self.assertEqual(results[1]['latitude'], 0.0)

    def test_filters(self):
        data = {
            'elements': [
                {'type': 'node', 'id': 1, 'lat': 1, 'lon': 1, 'tags': {'tourism': 'museum'}},
                {'type': 'node', 'id': 2, 'lat': 1, 'lon': 1, 'tags': {'name': 'X'}},
                {'type': 'node', 'id': 3, 'lat': 1, 'lon': 1, 'tags': {'name': 'X', 'tourism': 'hotel', 'disused': 'yes'}},
                {'type': 'node', 'id': 4, 'tags': {'name': 'X', 'tourism': 'hotel'}},
                {'type': 'other', 'id': 5},
            ]
        }
        self.assertEqual(parse_overpass(data, ORIGIN, 'lodging'), [])

    def test_address_and_image(self):
        data = {'elements': [{'type': 'node', 'id': 1, 'lat': 1, 'lon': 1, 'tags': {
            'name': 'X', 'tourism': 'hotel', 'addr:street': 'Main', 'addr:housenumber': '5', 'addr:city': 'Town',
            'image': 'https://img/x.jpg'}}]}
        [r] = parse_overpass(data, None, 'lodging')
        self.assertEqual(r['address'], 'Main 5, Town')
        self.assertEqual(r['photos'], ['https://img/x.jpg'])
        self.assertIsNone(r['distance_km'])
