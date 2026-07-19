from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from adventures.models import Location

from . import services
from .overpass_client import VALID_CATEGORIES


class NearbyPlacesView(APIView):
    """GET /api/places/nearby/?stop=<location_id>&category=<tourism|food|lodging>&radius=<meters>

    Cache-first Overpass lookup around an existing `Location` (stop). No LLM,
    no ranking — pure deterministic data per the blueprint's architectural
    principle (I1): this endpoint only fetches/caches facts from Overpass.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        stop_id = request.query_params.get('stop')
        category = request.query_params.get('category')
        radius = request.query_params.get('radius', '2000')

        if not stop_id:
            return Response({'error': "Parametro 'stop' e obrigatorio."}, status=400)
        if category not in VALID_CATEGORIES:
            return Response(
                {'error': f"Categoria invalida. Opcoes: {', '.join(VALID_CATEGORIES)}"}, status=400
            )

        try:
            radius = min(float(radius), 5000)
        except ValueError:
            return Response({'error': "Parametro 'radius' invalido."}, status=400)

        try:
            location = Location.objects.get(id=stop_id)
        except (Location.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Parada nao encontrada.'}, status=404)

        if location.user_id != request.user.id:
            return Response({'error': 'Sem permissao para esta parada.'}, status=403)

        if location.latitude is None or location.longitude is None:
            return Response({'error': 'Parada sem coordenadas.'}, status=400)

        result = services.get_nearby_places(location.latitude, location.longitude, radius, category)

        if result.get('error') and not result.get('results'):
            return Response(
                {'error': result['error'], 'count': 0, 'results': [], 'cached': result.get('cached', False)},
                status=503,
            )

        return Response(
            {
                'count': len(result['results']),
                'results': result['results'],
                'cached': result.get('cached', False),
            }
        )
