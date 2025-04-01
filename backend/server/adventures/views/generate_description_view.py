from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import requests

class GenerateDescription(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'],)
    def desc(self, request):
        name = self.request.query_params.get('name', '')
        # un url encode the name
        name = name.replace('%20', ' ')
        name = self.get_search_term(name)
        url = 'https://en.wikipedia.org/w/api.php?origin=*&action=query&prop=extracts&exintro&explaintext&format=json&titles=%s' % name
        response = requests.get(url)
        data = response.json()
        data = response.json()
        page_id = next(iter(data["query"]["pages"]))
        extract = data["query"]["pages"][page_id]
        if extract.get('extract') is None:
            return Response({"error": "No description found"}, status=400)
        return Response(extract)
    @action(detail=False, methods=['get'],)
    def img(self, request):
        name = self.request.query_params.get('name', '')
        # un url encode the name
        name = name.replace('%20', ' ')
        name = self.get_search_term(name)
        url = 'https://en.wikipedia.org/w/api.php?origin=*&action=query&prop=pageimages&format=json&piprop=original&titles=%s' % name
        response = requests.get(url)
        data = response.json()
        page_id = next(iter(data["query"]["pages"]))
        extract = data["query"]["pages"][page_id]
        if extract.get('original') is None:
            return Response({"error": "No image found"}, status=400)
        return Response(extract["original"])
    
    def get_search_term(self, term):
        response = requests.get(f'https://en.wikipedia.org/w/api.php?action=opensearch&search={term}&limit=10&namespace=0&format=json')
        data = response.json()
        if data[1] and len(data[1]) > 0:
            return data[1][0]