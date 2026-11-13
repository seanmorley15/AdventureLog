from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.models import EndurainIntegration, ImmichIntegration, StravaToken, WandererIntegration
from integrations.serializers import IntegrationStatusSerializer


def immich_web_url(server_url):
    """The Immich web app's address: the saved API address without its ``/api`` suffix."""
    url = (server_url or '').rstrip('/')
    return url[: -len('/api')] if url.endswith('/api') else url


class IntegrationStatusView(APIView):
    openapi_tags = ['Integrations']

    @extend_schema(responses=IntegrationStatusSerializer)
    def get(self, request):
        """
        Get your integrations

        Which outside services you have connected, and which the server supports.
        """
        immich = ImmichIntegration.objects.filter(user=request.user).first()
        return Response({
            'immich': {
                'exists': immich is not None,
                'copy_locally': immich.copy_locally if immich else False,
                # Links such as a place's spot on the Immich map (#1117).
                'web_url': immich_web_url(immich.server_url) if immich else None,
            },
            'google_maps': settings.GOOGLE_MAPS_API_KEY != '',
            'strava': {
                'global': settings.STRAVA_CLIENT_ID != '' and settings.STRAVA_CLIENT_SECRET != '',
                'user': StravaToken.objects.filter(user=request.user).exists(),
            },
            'wanderer': {'exists': WandererIntegration.objects.filter(user=request.user).exists()},
            'endurain': {'exists': EndurainIntegration.objects.filter(user=request.user).exists()},
        })
