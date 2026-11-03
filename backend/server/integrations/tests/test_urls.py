import uuid

from django.test import SimpleTestCase
from django.urls import resolve

from integrations.views import EndurainViewSet, ImmichViewSet, IntegrationStatusView, StravaViewSet, WandererViewSet

PREFIX = '/api/integrations'


class IntegrationRoutingTests(SimpleTestCase):
    """Each integration is one singleton viewset: the connection at its root, actions below it."""

    def view_for(self, path):
        match = resolve(path)
        actions = {method: action for method, action in (match.func.actions or {}).items() if method != 'head'}
        return match.func.cls, actions

    def test_immich_connection_and_actions(self):
        self.assertEqual(
            self.view_for(f'{PREFIX}/immich/'),
            (ImmichViewSet, {'get': 'retrieve', 'post': 'create', 'patch': 'partial_update', 'delete': 'destroy'}),
        )
        self.assertEqual(self.view_for(f'{PREFIX}/immich/search/'), (ImmichViewSet, {'get': 'search'}))
        self.assertEqual(self.view_for(f'{PREFIX}/immich/albums/'), (ImmichViewSet, {'get': 'albums'}))
        self.assertEqual(self.view_for(f'{PREFIX}/immich/albums/some-album/'), (ImmichViewSet, {'get': 'album'}))
        self.assertEqual(
            self.view_for(f'{PREFIX}/immich/assets/{uuid.uuid4()}/asset-1/'), (ImmichViewSet, {'get': 'asset'})
        )

    def test_overview_and_other_integrations(self):
        self.assertIs(resolve(f'{PREFIX}/').func.view_class, IntegrationStatusView)
        self.assertEqual(self.view_for(f'{PREFIX}/strava/authorize/'), (StravaViewSet, {'get': 'authorize'}))
        self.assertEqual(self.view_for(f'{PREFIX}/strava/')[0], StravaViewSet)
        self.assertEqual(self.view_for(f'{PREFIX}/wanderer/')[0], WandererViewSet)
        self.assertEqual(self.view_for(f'{PREFIX}/endurain/')[0], EndurainViewSet)
