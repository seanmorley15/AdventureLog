from rest_framework.test import APITestCase

from adventures.services.user_stats import UserStatsService
from core.geo import make_point
from users.models import CustomUser
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion
from worldtravel.visited import is_region_visited, umbrella_regions, visited_region_ids


class VisitedSyncTests(APITestCase):
    """Puerto Rico is a country and a region of the United States. Visits are made on the country."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='sync-user', email='sync-user@example.com', password='testpassword123'
        )
        self.other = CustomUser.objects.create_user(
            username='sync-other', email='sync-other@example.com', password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)

        self.us = Country.objects.create(name='United States', country_code='US', coordinates=make_point(-97.0, 38.0))
        self.pr = Country.objects.create(name='Puerto Rico', country_code='PR', coordinates=make_point(-66.5, 18.25))
        self.alabama = Region.objects.create(id='US-AL', name='Alabama', country=self.us)
        # The region under the United States has no cities of its own: the importer merges them onto the country.
        self.us_pr = Region.objects.create(id='US-PR', name='Puerto Rico', country=self.us, territory=self.pr)
        self.san_juan = Region.objects.create(id='PR-SJ', name='San Juan', country=self.pr)
        self.ponce = Region.objects.create(id='PR-PO', name='Ponce', country=self.pr)
        self.pr_san_juan = City.objects.create(id='PR-SJ-1', name='San Juan', region=self.san_juan)
        self.pr_ponce = City.objects.create(id='PR-PO-1', name='Ponce', region=self.ponce)
        self.mobile = City.objects.create(id='US-AL-1', name='Mobile', region=self.alabama)

    def _results(self, url):
        body = self.client.get(url).json()
        return body['results'] if isinstance(body, dict) and 'results' in body else body

    # --- regions

    def test_visiting_a_region_of_the_country_counts_for_the_region_of_the_parent(self):
        VisitedRegion.objects.create(user=self.user, region=self.san_juan)

        self.assertEqual(umbrella_regions(self.user.id), {'US-PR': self.us.id})
        self.assertTrue(is_region_visited(self.user.id, self.us_pr))
        self.assertEqual(visited_region_ids(self.user.id), {'PR-SJ', 'US-PR'})

    def test_it_shows_up_in_the_visited_regions_of_the_parent_and_not_in_another_countrys(self):
        VisitedRegion.objects.create(user=self.user, region=self.san_juan)

        in_us = self._results('/api/visited-regions/?country=US')
        in_pr = self._results('/api/visited-regions/?country=PR')

        self.assertEqual([row['region'] for row in in_us], ['US-PR'])
        self.assertEqual([row['region'] for row in in_pr], ['PR-SJ'])
        self.assertEqual(in_us[0]['name'], 'Puerto Rico')

    def test_a_region_the_user_marked_is_listed_once(self):
        VisitedRegion.objects.create(user=self.user, region=self.san_juan)
        VisitedRegion.objects.create(user=self.user, region=self.us_pr)

        rows = self._results('/api/visited-regions/?country=US')

        self.assertEqual([row['region'] for row in rows], ['US-PR'])
        self.assertEqual(umbrella_regions(self.user.id), {})

    def test_nothing_is_derived_without_a_visit(self):
        self.assertEqual(umbrella_regions(self.user.id), {})
        self.assertFalse(is_region_visited(self.user.id, self.us_pr))
        self.assertEqual(self._results('/api/visited-regions/'), [])

    def test_another_users_visits_do_not_count(self):
        VisitedRegion.objects.create(user=self.other, region=self.san_juan)

        self.assertEqual(umbrella_regions(self.user.id), {})

    def test_a_region_that_is_also_a_country_cannot_be_marked_on_the_parents_page(self):
        response = self.client.post('/api/visited-regions/', {'region': 'US-PR'}, format='json')

        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()['country_code'], 'PR')
        self.assertIn('Puerto Rico', response.json()['detail'])
        self.assertFalse(VisitedRegion.objects.exists())

    def test_the_regions_of_the_country_and_ordinary_regions_are_marked_as_before(self):
        self.assertEqual(self.client.post('/api/visited-regions/', {'region': 'PR-SJ'}, format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/visited-regions/', {'region': 'US-AL'}, format='json').status_code, 201)

        self.assertEqual(VisitedRegion.objects.filter(user=self.user).count(), 2)

    def test_a_region_visited_through_its_country_cannot_be_unmarked_on_its_own(self):
        VisitedRegion.objects.create(user=self.user, region=self.san_juan)

        response = self.client.delete('/api/visited-regions/US-PR/')

        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn('Puerto Rico', response.json()['detail'])
        self.assertTrue(VisitedRegion.objects.filter(user=self.user, region=self.san_juan).exists())

    def test_a_leftover_mark_nothing_backs_is_unmarked_as_before(self):
        VisitedRegion.objects.create(user=self.user, region=self.us_pr)

        response = self.client.delete('/api/visited-regions/US-PR/')

        self.assertEqual(response.status_code, 204, response.content)
        self.assertFalse(VisitedRegion.objects.filter(user=self.user).exists())

    def test_unmarking_the_regions_of_the_country_clears_the_parent_too(self):
        VisitedRegion.objects.create(user=self.user, region=self.san_juan)

        self.assertEqual(self.client.delete('/api/visited-regions/PR-SJ/').status_code, 204)

        self.assertEqual(umbrella_regions(self.user.id), {})
        self.assertEqual(self._results('/api/visited-regions/?country=US'), [])

    def test_the_regions_list_says_where_a_mirrored_region_is_marked(self):
        regions = {row['id']: row for row in self._results('/api/regions/?country=US')}

        self.assertEqual(regions['US-PR']['territory_country_code'], 'PR')
        self.assertEqual(regions['US-PR']['territory_country_name'], 'Puerto Rico')
        self.assertIsNone(regions['US-AL']['territory_country_code'])

    def test_country_progress_counts_the_visit_once_on_the_country_itself(self):
        VisitedRegion.objects.create(user=self.user, region=self.san_juan)

        countries = {row['country_code']: row for row in self._results('/api/countries/')}

        self.assertEqual(countries['PR']['num_visits'], 1)
        self.assertEqual(countries['US']['num_visits'], 0)
        self.assertEqual(countries['US']['num_regions'], 2)

    # --- cities

    def test_marking_a_city_of_the_country_marks_its_region_and_shows_on_the_parents_page(self):
        response = self.client.post('/api/visited-cities/', {'city': 'PR-PO-1'}, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            set(VisitedRegion.objects.filter(user=self.user).values_list('region_id', flat=True)), {'PR-PO'}
        )
        self.assertEqual([row['region'] for row in self._results('/api/visited-regions/?country=US')], ['US-PR'])

    # --- stats

    def test_stats_count_a_visit_once(self):
        VisitedRegion.objects.create(user=self.user, region=self.san_juan)
        VisitedCity.objects.create(user=self.user, city=self.pr_san_juan)

        stats = UserStatsService().build_user_stats(self.user, self.user, include_categories=False)

        self.assertEqual(stats['visited_region_count'], 1)
        self.assertEqual(stats['visited_city_count'], 1)
        self.assertEqual(stats['visited_country_count'], 1)

    def test_stats_do_not_count_a_leftover_mark_on_the_parents_side_again(self):
        VisitedRegion.objects.create(user=self.user, region=self.san_juan)
        VisitedRegion.objects.create(user=self.user, region=self.us_pr)

        stats = UserStatsService().build_user_stats(self.user, self.user, include_categories=False)

        self.assertEqual(stats['visited_region_count'], 1)
        self.assertEqual(stats['visited_country_count'], 1)

    def test_stats_count_a_mark_that_exists_only_on_the_parents_side_for_the_country(self):
        VisitedRegion.objects.create(user=self.user, region=self.us_pr)

        stats = UserStatsService().build_user_stats(self.user, self.user, include_categories=False)

        self.assertEqual(stats['visited_region_count'], 1)
        self.assertEqual(stats['visited_country_count'], 1)

    def test_stats_still_count_the_larger_country_for_its_own_regions(self):
        VisitedRegion.objects.create(user=self.user, region=self.san_juan)
        VisitedRegion.objects.create(user=self.user, region=self.alabama)

        stats = UserStatsService().build_user_stats(self.user, self.user, include_categories=False)

        self.assertEqual(stats['visited_region_count'], 2)
        self.assertEqual(stats['visited_country_count'], 2)

    def test_stats_for_a_user_with_no_territory_visits_are_unchanged(self):
        VisitedRegion.objects.create(user=self.user, region=self.alabama)
        VisitedCity.objects.create(user=self.user, city=self.mobile)

        stats = UserStatsService().build_user_stats(self.user, self.user, include_categories=False)

        self.assertEqual(stats['visited_region_count'], 1)
        self.assertEqual(stats['visited_city_count'], 1)
        self.assertEqual(stats['visited_country_count'], 1)
