from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import requests
from django.conf import settings
import urllib.parse

class GenerateDescription(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    # User-Agent header required by Wikipedia API
    HEADERS = {
        'User-Agent': f'AdventureLog/{settings.ADVENTURELOG_RELEASE_VERSION}'
    }

    @action(detail=False, methods=['get'])
    def desc(self, request):
        name = self.request.query_params.get('name', '')
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)
        
        # Properly URL decode the name
        name = urllib.parse.unquote(name)
        search_term = self.get_search_term(name)
        
        if not search_term:
            return Response({"error": "No matching Wikipedia article found"}, status=404)
        
        # Properly URL encode the search term for the API
        encoded_term = urllib.parse.quote(search_term)
        url = f'https://en.wikipedia.org/w/api.php?origin=*&action=query&prop=extracts&exintro&explaintext&format=json&titles={encoded_term}'
        
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return Response({"error": "No page data found"}, status=404)
            
            page_id = next(iter(pages))
            page_data = pages[page_id]
            
            # Check if page exists (page_id of -1 means page doesn't exist)
            if page_id == "-1":
                return Response({"error": "Wikipedia page not found"}, status=404)
            
            if not page_data.get('extract'):
                return Response({"error": "No description found"}, status=404)
            
            return Response(page_data)
            
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Failed to fetch data: {str(e)}"}, status=500)
        except ValueError as e:  # JSON decode error
            return Response({"error": "Invalid response from Wikipedia API"}, status=500)

    @action(detail=False, methods=['get'])
    def img(self, request):
        name = self.request.query_params.get('name', '')
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)
        
        # Properly URL decode the name
        name = urllib.parse.unquote(name)
        search_term = self.get_search_term(name)
        
        if not search_term:
            return Response({"error": "No matching Wikipedia article found"}, status=404)
        
        # Properly URL encode the search term for the API
        encoded_term = urllib.parse.quote(search_term)
        url = f'https://en.wikipedia.org/w/api.php?origin=*&action=query&prop=pageimages&format=json&piprop=original&titles={encoded_term}'
        
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return Response({"error": "No page data found"}, status=404)
            
            page_id = next(iter(pages))
            page_data = pages[page_id]
            
            # Check if page exists
            if page_id == "-1":
                return Response({"error": "Wikipedia page not found"}, status=404)
            
            original_image = page_data.get('original')
            if not original_image:
                return Response({"error": "No image found"}, status=404)
            
            return Response(original_image)
            
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Failed to fetch data: {str(e)}"}, status=500)
        except ValueError as e:  # JSON decode error
            return Response({"error": "Invalid response from Wikipedia API"}, status=500)
    
    def get_search_term(self, term):
        if not term:
            return None
        
        # Properly URL encode the search term
        encoded_term = urllib.parse.quote(term)
        url = f'https://en.wikipedia.org/w/api.php?action=opensearch&search={encoded_term}&limit=10&namespace=0&format=json'
        
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            
            # Check if response is empty
            if not response.text.strip():
                return None
                
            data = response.json()
            
            # OpenSearch API returns an array with 4 elements:
            # [search_term, [titles], [descriptions], [urls]]
            if len(data) >= 2 and data[1] and len(data[1]) > 0:
                return data[1][0]  # Return the first title match
            
            return None
            
        except requests.exceptions.RequestException:
            # If search fails, return the original term as fallback
            return term
        except ValueError:  # JSON decode error
            # If JSON parsing fails, return the original term as fallback
            return term