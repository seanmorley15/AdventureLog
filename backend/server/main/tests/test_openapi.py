"""
The API documents itself completely and truthfully.

- The schema generates without warnings and every operation is documented.
- Every DRF route is in the schema, and every hand-written (allauth) path still exists.
- ``openapi/schema.yaml`` is the committed copy; a change to the API shows up as a diff of it.
  Regenerate with ``python manage.py spectacular --file openapi/schema.yaml``.
- Real responses of the main endpoints match what the schema says they return.
"""

import difflib
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import jsonschema
import yaml
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.urls import Resolver404, resolve
from drf_spectacular.generators import EndpointEnumerator, SchemaGenerator
from drf_spectacular.renderers import OpenApiYamlRenderer
from rest_framework.test import APITestCase

from adventures.models import Collection, ContentImage, Location
from adventures.services.places.search import ProviderSearchResult
from core.testing import make_user
from main.openapi import TAGS

SCHEMA_FILE = Path(settings.BASE_DIR) / 'openapi' / 'schema.yaml'
METHODS = ('get', 'post', 'put', 'patch', 'delete')

_schema_cache = {}


def generated_schema():
    if 'schema' not in _schema_cache:
        _schema_cache['schema'] = SchemaGenerator().get_schema(request=None, public=True)
    return _schema_cache['schema']


def operations(schema):
    for path, item in schema['paths'].items():
        for method in METHODS:
            if method in item:
                yield path, method, item[method]


class SchemaCompletenessTests(SimpleTestCase):
    def test_the_committed_schema_is_up_to_date(self):
        # Generated fresh: other tests may have built the cached copy under overridden settings.
        schema = SchemaGenerator().get_schema(request=None, public=True)
        rendered = OpenApiYamlRenderer().render(schema, renderer_context={}).decode()
        committed = SCHEMA_FILE.read_text() if SCHEMA_FILE.exists() else ''
        if rendered != committed:
            diff = ''.join(list(difflib.unified_diff(
                committed.splitlines(True), rendered.splitlines(True), 'openapi/schema.yaml', 'generated', n=2
            ))[:60])
            self.fail(
                'openapi/schema.yaml is out of date. Run: python manage.py spectacular --file openapi/schema.yaml\n'
                + diff
            )

    def test_every_operation_is_documented(self):
        tag_names = {tag['name'] for tag in TAGS}
        problems = []
        for path, method, operation in operations(generated_schema()):
            where = f'{method.upper()} {path}'
            if not (operation.get('summary') or '').strip():
                problems.append(f'{where}: no summary (add a docstring or extend_schema(summary=...))')
            tags = operation.get('tags') or []
            if not tags or not set(tags) <= tag_names:
                problems.append(f'{where}: tags {tags} are not in main.openapi.TAGS')
            if 'security' not in operation:
                problems.append(f'{where}: does not say whether it needs authentication')
            # Signing out with allauth answers 401 by design ("you are now signed out").
            if not any(code.startswith('2') or code == '302' for code in operation.get('responses', {})) \
                    and operation.get('operationId') != 'allauth_session_delete':
                problems.append(f'{where}: no success response')
        self.assertEqual(problems, [], '\n' + '\n'.join(problems))

    def test_every_drf_route_is_in_the_schema(self):
        documented = {(path, method) for path, method, _ in operations(generated_schema())}
        # The documentation pages themselves are not part of the API they document.
        not_api = {'/api/schema/', '/api/docs/', '/api/docs/redoc/'}
        missing = []
        for path, _regex, method, _view in EndpointEnumerator().get_api_endpoints():
            # The schema names a primary key {id}, as drf-spectacular does by default.
            path = path.replace('{pk}', '{id}')
            if path not in not_api and (path, method.lower()) not in documented:
                missing.append(f'{method} {path}')
        self.assertEqual(missing, [], 'Routes left out of the schema: ' + ', '.join(missing))

    def test_hand_written_paths_still_exist(self):
        fragment = yaml.safe_load((Path(settings.BASE_DIR) / 'openapi' / 'allauth.yaml').read_text())
        gone = []
        for path in fragment['paths']:
            try:
                resolve(path)
            except Resolver404:
                gone.append(path)
        self.assertEqual(gone, [], 'openapi/allauth.yaml documents paths that no longer exist')


def _nullable_to_json_schema(node):
    """OpenAPI 3.0 writes `nullable: true`; JSON Schema writes the type as a list with null."""
    if isinstance(node, dict):
        node = {key: _nullable_to_json_schema(value) for key, value in node.items()}
        if node.pop('nullable', False):
            if 'type' in node:
                node['type'] = [node['type'], 'null']
            else:
                node = {'anyOf': [node, {'type': 'null'}]}
        return node
    if isinstance(node, list):
        return [_nullable_to_json_schema(value) for value in node]
    return node


class ContractTestCase(APITestCase):
    """Check a real response against the schema of that operation and status code."""

    def assertMatchesSchema(self, response, path, method):
        operation = generated_schema()['paths'][path][method]
        status = str(response.status_code)
        self.assertIn(status, operation['responses'], f'{method.upper()} {path} does not document {status}')
        content = operation['responses'][status].get('content', {})
        if not content:
            return
        body_schema = content['application/json']['schema']
        document = _nullable_to_json_schema(deepcopy({**body_schema, 'components': generated_schema()['components']}))
        jsonschema.validate(response.json(), document)


@override_settings(GOOGLE_MAPS_API_KEY='')
class ResponseContractTests(ContractTestCase):
    def setUp(self):
        self.owner = make_user('contract-owner')
        self.friend = make_user('contract-friend', public_profile=True)
        self.client.force_authenticate(user=self.owner)
        self.trip = Collection.objects.create(user=self.owner, name='Trip', type='trip')
        self.place = Location.objects.create(user=self.owner, name='Hut')
        self.place.collections.add(self.trip)

    def test_locations(self):
        created = self.client.post('/api/locations/', {'name': 'Lake'}, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        self.assertMatchesSchema(created, '/api/locations/', 'post')
        listed = self.client.get('/api/locations/', {'ordering': 'name'})
        self.assertMatchesSchema(listed, '/api/locations/', 'get')
        self.assertEqual(listed.json()['count'], 2)

    def test_collections_and_the_day_plan(self):
        listed = self.client.get('/api/collections/')
        self.assertMatchesSchema(listed, '/api/collections/', 'get')
        detail = self.client.get(f'/api/collections/{self.trip.id}/')
        self.assertMatchesSchema(detail, '/api/collections/{id}/', 'get')

        day = self.client.post(f'/api/collections/{self.trip.id}/days/', {}, format='json')
        self.assertEqual(day.status_code, 201, day.content)
        self.assertMatchesSchema(day, '/api/collections/{collection_id}/days/', 'post')

        item = self.client.post(
            f'/api/collections/{self.trip.id}/itinerary-items/',
            {'content_type': 'location', 'object_id': str(self.place.id), 'day_index': 1},
            format='json',
        )
        self.assertEqual(item.status_code, 201, item.content)
        self.assertMatchesSchema(item, '/api/collections/{collection_id}/itinerary-items/', 'post')

        reordered = self.client.post(
            f'/api/collections/{self.trip.id}/itinerary/reorder/',
            {'items': [{'id': item.json()['id'], 'day_index': 1, 'order': 0}]},
            format='json',
        )
        self.assertMatchesSchema(reordered, '/api/collections/{collection_id}/itinerary/reorder/', 'post')

    def test_the_sharing_flow(self):
        invited = self.client.post(
            f'/api/collections/{self.trip.id}/invites/', {'user': str(self.friend.uuid), 'role': 'viewer'}, format='json'
        )
        self.assertEqual(invited.status_code, 201, invited.content)
        self.assertMatchesSchema(invited, '/api/collections/{id}/invites/', 'post')

        self.client.force_authenticate(user=self.friend)
        invitations = self.client.get('/api/collections/invitations/')
        self.assertMatchesSchema(invitations, '/api/collections/invitations/', 'get')
        accepted = self.client.post(f'/api/collections/{self.trip.id}/invitation/accept/')
        self.assertMatchesSchema(accepted, '/api/collections/{id}/invitation/accept/', 'post')

        self.client.force_authenticate(user=self.owner)
        role = self.client.patch(
            f'/api/collections/{self.trip.id}/members/{self.friend.uuid}/', {'role': 'editor'}, format='json'
        )
        self.assertMatchesSchema(role, '/api/collections/{id}/members/{user_uuid}/', 'patch')
        removed = self.client.delete(f'/api/collections/{self.trip.id}/members/{self.friend.uuid}/')
        self.assertEqual(removed.status_code, 204)

    def test_the_account(self):
        self.assertMatchesSchema(self.client.get('/api/account/'), '/api/account/', 'get')
        self.assertMatchesSchema(self.client.get('/api/account/media-usage/'), '/api/account/media-usage/', 'get')
        self.client.force_authenticate(user=None)
        self.assertMatchesSchema(self.client.get('/api/auth/config/'), '/api/auth/config/', 'get')

    def test_place_search(self):
        result = ProviderSearchResult(
            results=[{'name': 'Eiffel Tower', 'display_name': 'Paris', 'lat': 48.85, 'lon': 2.29, 'place_id': 'x',
                      'type': 'attraction', 'types': [], 'category': None, 'description': None, 'website': None,
                      'phone_number': None, 'google_maps_url': None, 'importance': 0.9, 'rating': None,
                      'review_count': None, 'photos': [], 'addresstype': None, 'provider': 'osm',
                      'powered_by': 'OpenStreetMap'}],
            provider_used='osm',
            providers_attempted=['osm'],
        )
        with patch('adventures.views.places.search_places', return_value=result):
            response = self.client.get('/api/places/search/', {'q': 'eiffel'})
        self.assertMatchesSchema(response, '/api/places/search/', 'get')
        self.assertEqual(response.json()['count'], 1)


class ErrorContractTests(ContractTestCase):
    """Every error has the same body: detail and code, with fields on validation errors."""

    def setUp(self):
        self.owner = make_user('errors-owner')
        self.stranger = make_user('errors-stranger')
        self.place = Location.objects.create(user=self.owner, name='Hut')

    def test_400_validation(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/locations/', {'ordering': 'nope'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'validation_error')
        self.assertIn('ordering', response.json()['fields'])
        self.assertMatchesSchema(response, '/api/locations/', 'get')

    def test_401_without_credentials_and_with_a_bad_key(self):
        response = self.client.get('/api/locations/')
        self.assertEqual((response.status_code, response.json()['code']), (401, 'not_authenticated'))
        self.assertMatchesSchema(response, '/api/locations/', 'get')
        response = self.client.get('/api/locations/', HTTP_X_API_KEY='al_wrong')
        self.assertEqual((response.status_code, response.json()['code']), (401, 'authentication_failed'))

    def test_403_and_404(self):
        collection = Collection.objects.create(user=self.owner, name='Mine')
        viewer = make_user('errors-viewer')
        collection.shared_with.add(viewer)
        collection.members.filter(user=viewer).update(role='viewer')

        self.client.force_authenticate(user=viewer)
        forbidden = self.client.post(f'/api/collections/{collection.id}/days/', {}, format='json')
        self.assertEqual((forbidden.status_code, forbidden.json()['code']), (403, 'permission_denied'))
        self.assertMatchesSchema(forbidden, '/api/collections/{collection_id}/days/', 'post')

        self.client.force_authenticate(user=self.stranger)
        hidden = self.client.get(f'/api/locations/{self.place.id}/')
        self.assertEqual((hidden.status_code, hidden.json()['code']), (404, 'not_found'))
        self.assertMatchesSchema(hidden, '/api/locations/{id}/', 'get')

    def test_409_conflict(self):
        from worldtravel.models import Country, Region

        country = Country.objects.create(name='Iceland', country_code='IS')
        region = Region.objects.create(id='IS-1', name='Capital Region', country=country)
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.post('/api/visited-regions/', {'region': region.id}, format='json').status_code, 201)
        again = self.client.post('/api/visited-regions/', {'region': region.id}, format='json')
        self.assertEqual((again.status_code, again.json()['code']), (409, 'conflict'))
        self.assertMatchesSchema(again, '/api/visited-regions/', 'post')

    @override_settings(MEDIA_STORAGE_LIMIT_MB=0.001)
    def test_413_media_quota(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.owner)
        with patch('adventures.services.media_quota.get_media_storage_limit_bytes', return_value=10):
            response = self.client.post(
                '/api/attachments/',
                {'content_type': 'location', 'object_id': str(self.place.id),
                 'file': SimpleUploadedFile('big.txt', b'x' * 100)},
                format='multipart',
            )
        self.assertEqual((response.status_code, response.json()['code']), (413, 'media_quota_exceeded'))
        self.assertIn('limit_bytes', response.json())
        self.assertMatchesSchema(response, '/api/attachments/', 'post')
        self.assertFalse(ContentImage.objects.exists())
