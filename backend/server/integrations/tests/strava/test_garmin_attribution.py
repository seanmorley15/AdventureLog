from django.test import SimpleTestCase

from integrations.services.garmin import garmin_attribution
from integrations.views.strava import StravaViewSet


class GarminAttributionTests(SimpleTestCase):
    def test_garmin_device_is_named(self):
        self.assertEqual(garmin_attribution('Garmin Forerunner 965'), 'Garmin Forerunner 965')

    def test_brand_is_written_the_way_garmin_writes_it(self):
        self.assertEqual(garmin_attribution('garmin edge 540'), 'Garmin edge 540')

    def test_garmin_connect_upload_without_device_is_credited_to_garmin(self):
        self.assertEqual(garmin_attribution(None, 'garmin_ping_123456789'), 'Garmin')
        self.assertEqual(garmin_attribution('', 'garmin_push_42'), 'Garmin')

    def test_other_devices_get_no_credit(self):
        self.assertIsNone(garmin_attribution('Strava iPhone App', 'a1b2c3.fit'))
        self.assertIsNone(garmin_attribution('Wahoo ELEMNT BOLT'))
        self.assertIsNone(garmin_attribution(None, None))


class StravaActivityAttributionTests(SimpleTestCase):
    def extract(self, **activity):
        return StravaViewSet().extract_essential_activity_info({'id': 1, 'name': 'Run', **activity})

    def test_list_entry_carries_the_garmin_credit(self):
        info = self.extract(external_id='garmin_ping_99')
        self.assertEqual(info['external_id'], 'garmin_ping_99')
        self.assertEqual(info['garmin_attribution'], 'Garmin')

    def test_detailed_entry_names_the_device(self):
        info = self.extract(device_name='Garmin fenix 8', external_id='garmin_ping_99')
        self.assertEqual(info['garmin_attribution'], 'Garmin fenix 8')

    def test_non_garmin_entry_has_no_credit(self):
        self.assertIsNone(self.extract(device_name='Strava App')['garmin_attribution'])
