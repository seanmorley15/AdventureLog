import uuid

from django.test import SimpleTestCase
from django.urls import resolve

from integrations.views import (
    EndurainIntegrationViewSet,
    ImmichIntegrationView,
    ImmichIntegrationViewSet,
    IntegrationView,
    StravaIntegrationView,
    WandererIntegrationViewSet,
)

PREFIX = '/api/integrations'


class IntegrationRoutingTests(SimpleTestCase):
    """Each URL reaches the view the frontend expects, however the router orders them."""

    def view_for(self, path):
        return resolve(path).func.cls

    def test_immich_actions_win_over_the_crud_detail_route(self):
        self.assertIs(self.view_for(f'{PREFIX}/immich/search/'), ImmichIntegrationView)
        self.assertIs(self.view_for(f'{PREFIX}/immich/albums/'), ImmichIntegrationView)
        self.assertIs(self.view_for(f'{PREFIX}/immich/albums/some-album/'), ImmichIntegrationView)

    def test_immich_proxy_route(self):
        self.assertIs(
            self.view_for(f'{PREFIX}/immich/{uuid.uuid4()}/get/asset-1/'), ImmichIntegrationView
        )

    def test_immich_crud_routes(self):
        self.assertIs(self.view_for(f'{PREFIX}/immich/'), ImmichIntegrationViewSet)
        self.assertIs(self.view_for(f'{PREFIX}/immich/{uuid.uuid4()}/'), ImmichIntegrationViewSet)

    def test_overview_and_other_integrations(self):
        self.assertIs(self.view_for(f'{PREFIX}/'), IntegrationView)
        self.assertIs(self.view_for(f'{PREFIX}/strava/authorize/'), StravaIntegrationView)
        self.assertIs(self.view_for(f'{PREFIX}/wanderer/'), WandererIntegrationViewSet)
        self.assertIs(self.view_for(f'{PREFIX}/endurain/'), EndurainIntegrationViewSet)
