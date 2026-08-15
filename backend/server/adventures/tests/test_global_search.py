from rest_framework.test import APITestCase

from adventures.models import Checklist, Collection, Location, Lodging, Note
from users.models import CustomUser
from worldtravel.models import City, Country, Region, VisitedCity


class GlobalSearchAPITestCase(APITestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='search-owner',
            email='search-owner@example.com',
            password='testpassword123',
            public_profile=True,
            first_name='Search',
            last_name='Owner',
        )
        self.collaborator = CustomUser.objects.create_user(
            username='search-collab',
            email='search-collab@example.com',
            password='testpassword123',
        )
        self.country = Country.objects.create(name='France', country_code='FR')
        self.region = Region.objects.create(id='FR-75', name='Paris Region', country=self.country)
        self.city = City.objects.create(id='FR-75-paris', name='Paris City', region=self.region)

        self.collection = Collection.objects.create(
            user=self.owner,
            name='Europe Trip',
            description='Summer in Paris',
        )
        self.shared_collection = Collection.objects.create(
            user=self.owner,
            name='Shared Adventure',
            description='Collaborative plans',
        )
        self.shared_collection.shared_with.add(self.collaborator)

        self.location = Location.objects.create(
            user=self.owner,
            name='Eiffel Tower Visit',
            description='Evening lights in Paris',
            location='Paris, France',
            country=self.country,
        )
        self.note = Note.objects.create(
            user=self.owner,
            name='Paris Notes',
            content='Remember croissants',
            collection=self.collection,
        )
        self.lodging = Lodging.objects.create(
            user=self.owner,
            name='Left Bank Hotel',
            description='Near the Seine',
            collection=self.collection,
        )
        self.checklist = Checklist.objects.create(
            user=self.owner,
            name='Paris Packing List',
            collection=self.collection,
        )

        VisitedCity.objects.create(user=self.owner, city=self.city)

    def test_empty_query_returns_400(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/search/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Search query is required')

    def test_short_query_returns_400(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/search/?q=a')
        self.assertEqual(response.status_code, 400)
        self.assertIn('at least 2 characters', response.json()['error'])

    def test_location_hit_returns_lightweight_shape(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/search/?q=paris')
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload['query'], 'paris')
        self.assertIn('results', payload)
        self.assertIn('facets', payload)

        location_hits = [hit for hit in payload['results'] if hit['type'] == 'location']
        self.assertTrue(location_hits)
        hit = location_hits[0]
        self.assertEqual(hit['title'], 'Eiffel Tower Visit')
        self.assertEqual(hit['url'], f'/locations/{self.location.id}')
        self.assertIn('score', hit)
        self.assertNotIn('visits', hit)

    def test_shared_collection_searchable_by_collaborator(self):
        self.client.force_authenticate(user=self.collaborator)
        response = self.client.get('/api/search/?q=shared')
        self.assertEqual(response.status_code, 200)

        collection_hits = [hit for hit in response.json()['results'] if hit['type'] == 'collection']
        self.assertEqual(len(collection_hits), 1)
        self.assertEqual(collection_hits[0]['title'], 'Shared Adventure')
        self.assertTrue(collection_hits[0]['meta']['is_shared'])

    def test_city_hit_includes_visited_meta_without_visit_list(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/search/?q=paris')
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertNotIn('visited_cities', payload)
        self.assertNotIn('visited_regions', payload)

        city_hits = [hit for hit in payload['results'] if hit['type'] == 'city']
        self.assertTrue(city_hits)
        self.assertTrue(city_hits[0]['meta']['is_visited'])

    def test_types_filter_limits_results(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/search/?q=paris&types=note')
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertTrue(all(hit['type'] == 'note' for hit in payload['results']))
        self.assertEqual(payload['facets'].keys(), {'note'})

    def test_sub_entity_types_are_included(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/search/?q=paris')
        self.assertEqual(response.status_code, 200)

        result_types = {hit['type'] for hit in response.json()['results']}
        self.assertIn('note', result_types)
        self.assertIn('lodging', result_types)
        self.assertIn('checklist', result_types)

    def test_pagination_uses_offset(self):
        self.client.force_authenticate(user=self.owner)
        first_page = self.client.get('/api/search/?q=paris&limit=1&offset=0').json()
        second_page = self.client.get('/api/search/?q=paris&limit=1&offset=1').json()

        self.assertEqual(first_page['limit'], 1)
        self.assertEqual(first_page['offset'], 0)
        self.assertEqual(len(first_page['results']), 1)
        if second_page['results']:
            self.assertNotEqual(first_page['results'][0]['id'], second_page['results'][0]['id'])

    def test_partial_location_name_match(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/search/?q=eiff&types=location')
        self.assertEqual(response.status_code, 200)

        location_hits = [hit for hit in response.json()['results'] if hit['type'] == 'location']
        self.assertTrue(location_hits)
        self.assertEqual(location_hits[0]['title'], 'Eiffel Tower Visit')

    def test_query_alias_still_works(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/search/?query=eiffel')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(hit['type'] == 'location' for hit in response.json()['results']))

    def test_locations_rank_before_other_entity_types(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/search/?q=paris&limit=20')
        self.assertEqual(response.status_code, 200)

        results = response.json()['results']
        self.assertTrue(results)
        types = [hit['type'] for hit in results]
        if 'location' in types and len(set(types)) > 1:
            first_non_location = next(i for i, t in enumerate(types) if t != 'location')
            self.assertEqual(types[0], 'location')
            self.assertTrue(all(t == 'location' for t in types[:first_non_location]))
