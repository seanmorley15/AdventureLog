import logging
import urllib.parse
import requests
from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from adventures.throttling import ExternalWikipediaThrottle
from adventures.services.wikipedia.description_service import WikipediaDescriptionService

logger = logging.getLogger(__name__)


class GenerateDescription(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], throttle_classes=[ExternalWikipediaThrottle])
    def desc(self, request):
        name = request.query_params.get('name', '')
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)

        name = urllib.parse.unquote(name).strip()
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)

        service = WikipediaDescriptionService()
        lang = service.get_language(request.query_params.get('lang'))

        try:
            page = service.get_description(name, lang)
            if page:
                return Response(page)
            return Response({"error": "No description found"}, status=404)
        except requests.exceptions.RequestException:
            logger.exception("Failed to fetch data from Wikipedia")
            return Response({"error": "Failed to fetch data from Wikipedia."}, status=500)
        except ValueError:
            return Response({"error": "Invalid response from Wikipedia API"}, status=500)

    @action(detail=False, methods=['get'], throttle_classes=[ExternalWikipediaThrottle])
    def img(self, request):
        name = request.query_params.get('name', '')
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)

        name = urllib.parse.unquote(name).strip()
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)

        service = WikipediaDescriptionService()
        lang = service.get_language(request.query_params.get('lang'))

        try:
            images = service.get_images(name, lang)
            if images:
                return Response({"images": images})
            return Response({"error": "No image found"}, status=404)
        except requests.exceptions.RequestException:
            logger.exception("Failed to fetch data from Wikipedia")
            return Response({"error": "Failed to fetch data from Wikipedia."}, status=500)
        except ValueError:
            return Response({"error": "Invalid response from Wikipedia API"}, status=500)