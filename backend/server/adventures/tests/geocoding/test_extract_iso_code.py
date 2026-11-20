from django.test import TestCase

from adventures.services.geocoding.matching import extract_iso_code
from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import City, Country, Region


class ExtractIsoCodeTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='geocode-user',
            email='geocode-user@example.com',
            password='testpassword123',
        )
        self.gibraltar = Country.objects.create(name='Gibraltar', country_code='GI')
        Region.objects.create(id='GI-00', name='Gibraltar', country=self.gibraltar)

        # Finland is here so that an Åland point has a reported country with its own regions.
        finland = Country.objects.create(name='Finland', native_name='Suomi', country_code='FI', coordinates=make_point(26.0, 64.0))
        Region.objects.create(id='FI-18', name='Uusimaa', country=finland, coordinates=make_point(24.94, 60.17))
        Region.objects.create(id='FI-19', name='Finland Proper', country=finland, coordinates=make_point(22.27, 60.45))
        # dr5hn v3.2 municipalities for AX. Mariehamn's imported city id is AX-01-160425.
        aland = Country.objects.create(
            name='Aland Islands', native_name='Åland', country_code='AX', coordinates=make_point(19.9, 60.1167)
        )
        aland_municipalities = (
            ('01', 'Mariehamn'),
            ('02', 'Jomala'),
            ('03', 'Finström'),
            ('04', 'Lemland'),
            ('05', 'Saltvik'),
            ('06', 'Hammarland'),
            ('07', 'Sund'),
            ('08', 'Eckerö'),
            ('09', 'Föglö'),
            ('10', 'Geta'),
            ('11', 'Vårdö'),
            ('12', 'Brändö'),
            ('13', 'Lumparland'),
            ('14', 'Kumlinge'),
            ('15', 'Kökar'),
            ('16', 'Sottunga'),
        )
        mariehamn = None
        for iso2, name in aland_municipalities:
            region = Region.objects.create(
                id=f'AX-{iso2}', name=name, country=aland, coordinates=make_point(19.94, 60.10) if iso2 == '01' else None
            )
            if iso2 == '01':
                mariehamn = region
        City.objects.create(id='AX-01-160425', name='Mariehamn', region=mariehamn, coordinates=make_point(19.9496, 60.0973))
        curacao = Country.objects.create(name='Curaçao', country_code='CW')
        Region.objects.create(id='CW-00', name='Curaçao', country=curacao)
        sint_maarten = Country.objects.create(name='Sint Maarten (Dutch part)', native_name='Sint Maarten', country_code='SX')
        Region.objects.create(id='SX-00', name='Sint Maarten (Dutch part)', country=sint_maarten)

        # Puerto Rico is a country of its own and also a region of the United States.
        united_states = Country.objects.create(name='United States', country_code='US', coordinates=make_point(-97.0, 38.0))
        pr = Country.objects.create(name='Puerto Rico', country_code='PR', coordinates=make_point(-66.5, 18.25))
        Region.objects.create(id='US-AL', name='Alabama', country=united_states, coordinates=make_point(-86.8, 32.8))
        Region.objects.create(id='US-PA', name='Pennsylvania', country=united_states, coordinates=make_point(-77.2, 41.0))
        Region.objects.create(id='US-PR', name='Puerto Rico', country=united_states, territory=pr, coordinates=make_point(-66.5, 18.25))
        us_minor = Country.objects.create(name='United States Minor Outlying Islands', country_code='UM')
        Region.objects.create(
            id='US-UM', name='United States Minor Outlying Islands', country=united_states,
            territory=us_minor, coordinates=make_point(-177.37, 28.21),
        )
        Region.objects.create(id='UM-71', name='Midway Islands', country=us_minor, coordinates=make_point(-177.37, 28.21))
        Region.objects.create(id='UM-79', name='Wake Island', country=us_minor, coordinates=make_point(166.65, 19.28))
        puerto_rico_san_juan = Region.objects.create(id='PR-SJ', name='San Juan', country=pr, coordinates=make_point(-66.1, 18.45))
        Region.objects.create(id='PR-PO', name='Ponce', country=pr, coordinates=make_point(-66.6, 18.0))
        City.objects.create(id='PR-SJ-1', name='San Juan', region=puerto_rico_san_juan, coordinates=make_point(-66.1, 18.45))

    def _assert_mariehamn(self, result):
        self.assertEqual(result['region_id'], 'AX-01')
        self.assertEqual(result['region'], 'Mariehamn')
        self.assertEqual(result['country_id'], 'AX')
        self.assertEqual(result['city'], 'Mariehamn')
        self.assertEqual(result['city_id'], 'AX-01-160425')

    def test_country_without_subdivisions_uses_its_single_region(self):
        # Nominatim reverse result for 36.128593, -5.347476: no ISO3166 keys at all
        data = {
            'address': {
                'road': 'Royal Anglian Way',
                'city': 'Gibraltar',
                'country': 'Gibraltar',
                'country_code': 'gi',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'GI-00')
        self.assertEqual(result['country_id'], 'GI')

    def test_unknown_country_still_reports_no_region(self):
        data = {'address': {'country': 'Nowhere', 'country_code': 'zz'}}

        self.assertEqual(extract_iso_code(self.user, data), {'error': 'No region found'})

    def test_unknown_country_is_not_second_guessed_from_the_position(self):
        # A country the dataset does not know is left alone, even right next to one it does.
        data = {'address': {'country': 'Nowhere', 'country_code': 'zz'}}

        self.assertEqual(extract_iso_code(self.user, data, lat=18.45, lon=-66.1), {'error': 'No region found'})

    def test_aland_finnish_subdivision_code_matches_mariehamn(self):
        # Nominatim reverse (zoom 18) for Mariehamn (60.102423, 19.941260), see #1212.
        # "Mariehamn sub-region" is the sub-region; the municipality itself is the town.
        data = {
            'address': {
                'suburb': 'Vreten',
                'city_district': 'Vreten',
                'town': 'Mariehamn',
                'municipality': 'Mariehamn sub-region',
                'county': 'Åland Islands',
                'ISO3166-2-lvl3': 'FI-01',
                'state': 'Åland Islands',
                'ISO3166-2-lvl4': 'FI-01',
                'country': 'Finland',
                'country_code': 'fi',
            }
        }

        self._assert_mariehamn(extract_iso_code(self.user, data))
        self._assert_mariehamn(extract_iso_code(self.user, data, lat=60.102423, lon=19.94126))

    def test_aland_matches_with_finnish_language_response(self):
        # Same point with Accept-Language: fi. Every name is Finnish, so none can be matched to the
        # dataset by name, and the country is settled by the position instead. The city name cannot
        # be matched either, so the result is the region.
        data = {
            'address': {
                'suburb': 'Vreten',
                'city_district': 'Vreten',
                'town': 'Maarianhamina',
                'municipality': 'Maarianhaminan kaupunki',
                'county': 'Ahvenanmaa',
                'ISO3166-2-lvl3': 'FI-01',
                'state': 'Ahvenanmaa',
                'ISO3166-2-lvl4': 'FI-01',
                'country': 'Suomi',
                'country_code': 'fi',
            }
        }

        result = extract_iso_code(self.user, data, lat=60.102423, lon=19.94126)

        self.assertEqual(result['region_id'], 'AX-01')
        self.assertEqual(result['region'], 'Mariehamn')
        self.assertEqual(result['country_id'], 'AX')

    def test_aland_town_selects_municipality_inside_a_shared_subregion(self):
        # Jomala's municipality field is the countryside sub-region, not Jomala itself.
        data = {
            'address': {
                'town': 'Jomala',
                'municipality': 'Ålands Countryside',
                'county': 'Åland Islands',
                'ISO3166-2-lvl3': 'FI-01',
                'state': 'Åland Islands',
                'ISO3166-2-lvl4': 'FI-01',
                'country': 'Finland',
                'country_code': 'fi',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'AX-02')
        self.assertEqual(result['region'], 'Jomala')
        self.assertEqual(result['country_id'], 'AX')
        self.assertIsNone(result['city'])

    def test_aland_municipality_field_matches_when_town_is_absent(self):
        # Smaller municipalities come back as the municipality boundary, with no town.
        data = {
            'address': {
                'municipality': 'Finström',
                'ISO3166-2-lvl4': 'FI-01',
                'state': 'Åland Islands',
                'country': 'Finland',
                'country_code': 'fi',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'AX-03')
        self.assertEqual(result['region'], 'Finström')
        self.assertEqual(result['country_id'], 'AX')
        self.assertIsNone(result['city'])

    def test_curacao_dutch_subdivision_code_matches_curacao_country(self):
        data = {
            'address': {
                'city': 'Willemstad',
                'ISO3166-2-lvl3': 'NL-CW',
                'country': 'Curaçao',
                'country_code': 'nl',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'CW-00')
        self.assertEqual(result['country_id'], 'CW')

    def test_sint_maarten_dutch_subdivision_code_matches_sint_maarten_country(self):
        # Nominatim search for Philipsburg: town and municipality, subdivision NL-SX.
        data = {
            'address': {
                'town': 'Philipsburg',
                'municipality': 'Philipsburg',
                'country': 'Sint Maarten',
                'ISO3166-2-lvl3': 'NL-SX',
                'country_code': 'nl',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'SX-00')
        self.assertEqual(result['country_id'], 'SX')

    def test_puerto_rico_resolves_to_its_own_country(self):
        # The dataset lists Puerto Rico as a country and as a region of the United States, and
        # the region is linked to the country. OSM reports it under the United States.
        data = {
            'address': {
                'city': 'San Juan',
                'state': 'Puerto Rico',
                'ISO3166-2-lvl4': 'US-PR',
                'country': 'United States',
                'country_code': 'us',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'PR-SJ')
        self.assertEqual(result['country_id'], 'PR')
        self.assertEqual(result['city_id'], 'PR-SJ-1')

    def test_puerto_rico_from_google_matches_the_osm_result(self):
        # Google reports Puerto Rico under the United States with the state's name as its short code.
        google = {
            'address': {
                'country': 'United States',
                'ISO3166-1': 'US',
                'state': 'Puerto Rico',
                'ISO3166-2-lvl1': 'US-PR',
                'city': 'San Juan',
            }
        }
        osm = {
            'address': {
                'city': 'San Juan', 'state': 'Puerto Rico', 'ISO3166-2-lvl4': 'US-PR',
                'country': 'United States', 'country_code': 'us',
            }
        }

        self.assertEqual(extract_iso_code(self.user, google)['region_id'], extract_iso_code(self.user, osm)['region_id'])
        self.assertEqual(extract_iso_code(self.user, google)['country_id'], 'PR')

    def test_territory_is_found_from_the_parents_state_name_when_the_code_is_unknown(self):
        france = Country.objects.create(name='France', country_code='FR', coordinates=make_point(2.0, 46.0))
        guadeloupe = Country.objects.create(name='Guadeloupe', country_code='GP', coordinates=make_point(-61.58, 16.25))
        Region.objects.create(id='FR-01', name='Ain', country=france)
        Region.objects.create(id='FR-02', name='Aisne', country=france)
        Region.objects.create(id='FR-971', name='Guadeloupe', country=france, territory=guadeloupe)
        Region.objects.create(id='GP-01', name='Basse-Terre', country=guadeloupe)
        pointe = Region.objects.create(id='GP-02', name='Pointe-à-Pitre', country=guadeloupe)
        City.objects.create(id='GP-02-1', name='Pointe-à-Pitre', region=pointe)
        data = {
            'address': {
                'country': 'France',
                'ISO3166-1': 'FR',
                'state': 'Guadeloupe',
                'ISO3166-2-lvl1': 'FR-Guadeloupe',
                'city': 'Pointe-à-Pitre',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['country_id'], 'GP')
        self.assertEqual(result['region_id'], 'GP-02')
        self.assertEqual(result['city_id'], 'GP-02-1')

    def test_region_named_like_a_country_is_not_a_territory(self):
        # Nothing links the Georgia region of the US to the country, so it stays in the US.
        georgia = Country.objects.create(name='Georgia', country_code='GE', coordinates=make_point(43.5, 42.0))
        Region.objects.create(id='GE-TB', name='Tbilisi', country=georgia)
        Region.objects.get_or_create(
            id='US-GA', defaults={'name': 'Georgia', 'country': Country.objects.get(country_code='US')}
        )
        data = {
            'address': {
                'city': 'Atlanta', 'state': 'Georgia', 'ISO3166-2-lvl4': 'US-GA',
                'country': 'United States', 'country_code': 'us',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['country_id'], 'US')
        self.assertEqual(result['region_id'], 'US-GA')

    def test_subdivision_named_by_county_when_there_is_no_state(self):
        # Montserrat from Nominatim: no state and no ISO3166-2 key, only the parish as the county.
        montserrat = Country.objects.create(name='Montserrat', native_name='Montserrat', country_code='MS')
        Region.objects.create(id='MS-03', name='Saint Anthony', country=montserrat)
        Region.objects.create(id='MS-02', name='Saint Georges', country=montserrat)
        Region.objects.create(id='MS-01', name='Saint Peter', country=montserrat)
        data = {
            'address': {
                'hamlet': "Carr's Bay",
                'town': 'Brades',
                'county': 'Saint Peter',
                'country': 'Montserrat',
                'country_code': 'ms',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'MS-01')
        self.assertEqual(result['country_id'], 'MS')

    def test_montserrat_from_google_matches_the_osm_result(self):
        montserrat = Country.objects.create(name='Montserrat', country_code='MS')
        Region.objects.create(id='MS-02', name='Saint Georges', country=montserrat)
        Region.objects.create(id='MS-01', name='Saint Peter', country=montserrat)
        data = {
            'address': {
                'country': 'Montserrat',
                'ISO3166-1': 'MS',
                'state': 'Saint Peter',
                'ISO3166-2-lvl1': 'MS-Saint Peter',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'MS-01')

    def test_territory_reported_under_the_netherlands_is_found_by_its_country_name(self):
        aruba = Country.objects.create(name='Aruba', country_code='AW')
        Region.objects.create(id='AW-01', name='Noord', country=aruba)
        oranjestad = Region.objects.create(id='AW-09', name='Oranjestad', country=aruba)
        data = {
            'address': {
                'town': 'Oranjestad', 'country': 'Aruba', 'ISO3166-2-lvl3': 'NL-AW', 'country_code': 'nl',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['country_id'], 'AW')
        self.assertEqual(result['region_id'], oranjestad.id)

    def test_dutch_caribbean_municipality_is_matched_by_name_not_by_its_iso_code(self):
        bq = Country.objects.create(name='Bonaire, Sint Eustatius and Saba', country_code='BQ')
        bonaire = Region.objects.create(id='BQ-BQ1', name='Bonaire', country=bq)
        Region.objects.create(id='BQ-BQ2', name='Saba', country=bq)
        data = {
            'address': {
                'town': 'Kralendijk', 'municipality': 'Bonaire', 'ISO3166-2-lvl8': 'BQ-BO',
                'country': 'Nederland', 'country_code': 'nl',
            }
        }

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['country_id'], 'BQ')
        self.assertEqual(result['region_id'], bonaire.id)

    def test_territory_of_another_country_is_found_from_its_territory_field(self):
        australia = Country.objects.create(name='Australia', country_code='AU', coordinates=make_point(133.0, -25.0))
        Region.objects.create(id='AU-NSW', name='New South Wales', country=australia)
        Region.objects.create(id='AU-VIC', name='Victoria', country=australia)
        norfolk = Country.objects.create(name='Norfolk Island', country_code='NF', coordinates=make_point(167.95, -29.03))
        Region.objects.create(id='NF-00', name='Norfolk Island', country=norfolk)
        data = {
            'address': {
                'town': 'Burnt Pine', 'territory': 'Norfolk Island', 'country': 'Australia', 'country_code': 'au',
            }
        }

        result = extract_iso_code(self.user, data, lat=-29.0564, lon=167.9595)

        self.assertEqual(result['country_id'], 'NF')
        self.assertEqual(result['region_id'], 'NF-00')

    def test_an_address_that_names_another_country_does_not_leave_the_country_the_point_is_in(self):
        # A county called Mexico in Missouri is not Mexico. With nothing else to go on, the place
        # is nearer the United States, so the result stays there.
        mexico = Country.objects.create(name='Mexico', country_code='MX', coordinates=make_point(-102.0, 23.0))
        Region.objects.create(id='MX-AGU', name='Aguascalientes', country=mexico)
        data = {'address': {'county': 'Mexico', 'country': 'United States', 'country_code': 'us'}}

        result = extract_iso_code(self.user, data, lat=39.17, lon=-91.88)

        self.assertEqual(result['country_id'], 'US')
        self.assertIsNone(result['region_id'])

    def test_iso_code_that_differs_only_in_leading_zeros_matches(self):
        mongolia = Country.objects.create(name='Mongolia', country_code='MN')
        Region.objects.create(id='MN-073', name='Arkhangai', country=mongolia)
        ulaanbaatar = Region.objects.create(id='MN-001', name='Ulaanbaatar', country=mongolia)
        data = {'address': {'city': 'Улаанбаатар', 'ISO3166-2-lvl4': 'MN-1', 'country_code': 'mn'}}

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], ulaanbaatar.id)

    def test_region_name_with_trailing_space_and_a_division_word_matches(self):
        bangladesh = Country.objects.create(name='Bangladesh', country_code='BD')
        dhaka = Region.objects.create(id='BD-C', name='Dhaka ', country=bangladesh)
        Region.objects.create(id='BD-D', name='Khulna ', country=bangladesh)
        data = {'address': {'state': 'Dhaka Division', 'country_code': 'bd'}}

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], dhaka.id)

    def test_most_specific_locality_decides_the_region(self):
        # "Singapore" is also the name of a city in another region, but the suburb is more specific.
        singapore = Country.objects.create(name='Singapore', country_code='SG')
        central = Region.objects.create(id='SG-01', name='Central Singapore', country=singapore)
        north_west = Region.objects.create(id='SG-03', name='North West', country=singapore)
        City.objects.create(id='SG-01-1', name='Singapore', region=central)
        City.objects.create(id='SG-03-1', name='Sembawang', region=north_west)
        data = {'address': {'suburb': 'Sembawang', 'borough': 'North Region', 'city': 'Singapore', 'country_code': 'sg'}}

        result = extract_iso_code(self.user, data)

        self.assertEqual(result['region_id'], 'SG-03')

    def test_nearest_city_settles_a_place_whose_names_match_nothing(self):
        cayman = Country.objects.create(name='Cayman Islands', country_code='KY')
        grand_cayman = Region.objects.create(id='KY-01', name='Grand Cayman', country=cayman)
        Region.objects.create(id='KY-02', name='Cayman Brac', country=cayman)
        City.objects.create(id='KY-01-1', name='Bodden Town', region=grand_cayman, coordinates=make_point(-81.25, 19.28))
        data = {'address': {'suburb': 'Rock Hole', 'city': 'George Town', 'country': 'Cayman Islands', 'country_code': 'ky'}}

        result = extract_iso_code(self.user, data, lat=19.29, lon=-81.26)

        self.assertEqual(result['region_id'], 'KY-01')
        self.assertIsNone(result['city_id'])

    def test_a_place_far_from_every_city_has_no_region_but_keeps_its_country(self):
        saint_helena = Country.objects.create(name='Saint Helena', country_code='SH')
        Region.objects.create(id='SH-01', name='Alarm Forest', country=saint_helena, coordinates=make_point(-5.7, -15.95))
        Region.objects.create(id='SH-04', name='Jamestown', country=saint_helena, coordinates=make_point(-5.72, -15.92))
        data = {
            'address': {
                'town': 'Georgetown', 'region': 'Ascension', 'ISO3166-2-lvl3': 'SH-AC',
                'country': 'Saint Helena, Ascension and Tristan da Cunha', 'country_code': 'sh',
            }
        }

        result = extract_iso_code(self.user, data, lat=-7.9278, lon=-14.4147)

        self.assertEqual(result['country_id'], 'SH')
        self.assertIsNone(result['region_id'])
        self.assertIsNone(result['region'])
        self.assertIsNone(result['city_id'])
        self.assertEqual(result['display_name'], 'Saint Helena, SH')

    def test_island_group_reported_under_a_bare_country_is_found_by_position(self):
        # Midway comes back as {country: United States} alone, and "United States Minor Outlying
        # Islands" is a US region that the dataset links to a country of its own.
        data = {'address': {'historic': 'Midway National Memorial', 'country': 'United States', 'country_code': 'us'}}

        result = extract_iso_code(self.user, data, lat=28.2101, lon=-177.3761)

        self.assertEqual(result['country_id'], 'UM')
        self.assertEqual(result['region_id'], 'UM-71')

    def test_a_named_place_is_not_handed_to_a_country_the_provider_did_not_report(self):
        # The position is right next to Mariehamn, but the provider said United States and named a
        # place, so the position is not allowed to overrule it.
        data = {'address': {'city': 'Nowheresville', 'country': 'United States', 'country_code': 'us'}}

        result = extract_iso_code(self.user, data, lat=60.1, lon=19.94)

        self.assertEqual(result['country_id'], 'US')
        self.assertIsNone(result['region_id'])
