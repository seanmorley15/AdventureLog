from django.test import SimpleTestCase

from adventures.services.recommendations.merge import merge_results, names_match, normalize_name


def place(name, lat, lon, source='google', **extra):
    return {'id': f'{source}:{name}', 'external_id': name, 'source': source, 'name': name, 'latitude': lat,
            'longitude': lon, **extra}


class MergeTests(SimpleTestCase):
    def test_name_normalization(self):
        self.assertEqual(normalize_name('  Café  de l’Époque! '), 'cafe de l epoque')

    def test_names_match(self):
        self.assertTrue(names_match('Café Central', 'Cafe Central'))
        self.assertTrue(names_match('Hotel Lux', 'Hotel Lux Berlin'))
        self.assertFalse(names_match('Louvre', 'Orsay'))
        self.assertFalse(names_match('', 'X'))

    def test_merges_same_place_and_fills_gaps(self):
        g = place('Cafe Central', 48.0, 2.0, website=None, phone_number='1')
        o = place('Café Central', 48.0001, 2.0001, source='osm', website='https://x', phone_number='2')
        [merged] = merge_results([g], [o])
        self.assertEqual(merged['source'], 'google')
        self.assertEqual(merged['sources'], ['google', 'osm'])
        self.assertEqual(merged['website'], 'https://x')
        self.assertEqual(merged['phone_number'], '1')

    def test_keeps_both_when_far_apart_or_different(self):
        g = place('Cafe Central', 48.0, 2.0)
        far = place('Cafe Central', 48.01, 2.0, source='osm')
        other = place('Bakery', 48.0, 2.0, source='osm')
        self.assertEqual(len(merge_results([g], [far, other])), 3)

    def test_osm_only_results_pass_through(self):
        [r] = merge_results([], [place('X', 1, 1, source='osm')])
        self.assertEqual(r['sources'], ['osm'])
