import logging
import re
import urllib.parse
from difflib import SequenceMatcher

import requests
from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)

class GenerateDescription(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    # User-Agent header required by Wikipedia API, Accept-Language patched in per request
    BASE_HEADERS = {
        'User-Agent': f'AdventureLog/{getattr(settings, "ADVENTURELOG_RELEASE_VERSION", "unknown")}'
    }
    DEFAULT_LANGUAGE = "en"
    LANGUAGE_PATTERN = re.compile(r"^[a-z0-9-]{2,12}$", re.IGNORECASE)
    MAX_CANDIDATES = 10  # Increased to find better matches
    
    # Accepted image formats (no SVG)
    ACCEPTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    MIN_DESCRIPTION_LENGTH = 50  # Minimum characters for a valid description

    @action(detail=False, methods=['get'])
    def desc(self, request):
        name = self.request.query_params.get('name', '')
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)
        
        name = urllib.parse.unquote(name).strip()
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)

        lang = self.get_language(request)

        try:
            candidates = self.get_candidate_pages(name, lang)
            
            for candidate in candidates:
                page_data = self.fetch_page(
                    lang=lang,
                    candidate=candidate,
                    props='extracts|categories',
                    extra_params={'exintro': 1, 'explaintext': 1}
                )
                if not page_data or page_data.get('missing'):
                    continue

                # Check if this is a disambiguation page
                if self.is_disambiguation_page(page_data):
                    continue

                extract = (page_data.get('extract') or '').strip()
                
                # Filter out pages with very short descriptions
                if len(extract) < self.MIN_DESCRIPTION_LENGTH:
                    continue

                # Filter out list/index pages
                if self.is_list_or_index_page(page_data):
                    continue

                page_data['lang'] = lang
                return Response(page_data)

            return Response({"error": "No description found"}, status=404)

        except requests.exceptions.RequestException:
            logger.exception("Failed to fetch data from Wikipedia")
            return Response({"error": "Failed to fetch data from Wikipedia."}, status=500)
        except ValueError:
            return Response({"error": "Invalid response from Wikipedia API"}, status=500)

    @action(detail=False, methods=['get'])
    def img(self, request):
        name = self.request.query_params.get('name', '')
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)
        
        name = urllib.parse.unquote(name).strip()
        if not name:
            return Response({"error": "Name parameter is required"}, status=400)

        lang = self.get_language(request)

        try:
            candidates = self.get_candidate_pages(name, lang)
            
            for candidate in candidates:
                page_data = self.fetch_page(
                    lang=lang,
                    candidate=candidate,
                    props='pageimages|categories',
                    extra_params={'piprop': 'original|thumbnail', 'pithumbsize': 640}
                )
                if not page_data or page_data.get('missing'):
                    continue

                # Skip disambiguation pages
                if self.is_disambiguation_page(page_data):
                    continue

                # Skip list/index pages
                if self.is_list_or_index_page(page_data):
                    continue

                # Try original image first
                original_image = page_data.get('original')
                if original_image and self.is_valid_image(original_image.get('source')):
                    return Response(original_image)

                # Fall back to thumbnail
                thumbnail_image = page_data.get('thumbnail')
                if thumbnail_image and self.is_valid_image(thumbnail_image.get('source')):
                    return Response(thumbnail_image)

            return Response({"error": "No image found"}, status=404)

        except requests.exceptions.RequestException:
            logger.exception("Failed to fetch data from Wikipedia")
            return Response({"error": "Failed to fetch data from Wikipedia."}, status=500)
        except ValueError:
            return Response({"error": "Invalid response from Wikipedia API"}, status=500)

    def is_valid_image(self, image_url):
        """Check if image URL is valid and not an SVG"""
        if not image_url:
            return False
        
        url_lower = image_url.lower()
        
        # Reject SVG images
        if '.svg' in url_lower:
            return False
        
        # Accept only specific image formats
        return any(url_lower.endswith(fmt) or fmt in url_lower for fmt in self.ACCEPTED_IMAGE_FORMATS)

    def is_disambiguation_page(self, page_data):
        """Check if page is a disambiguation page"""
        categories = page_data.get('categories', [])
        for cat in categories:
            cat_title = cat.get('title', '').lower()
            if 'disambiguation' in cat_title or 'disambig' in cat_title:
                return True
        
        # Check title for disambiguation indicators
        title = page_data.get('title', '').lower()
        if '(disambiguation)' in title:
            return True
        
        return False

    def is_list_or_index_page(self, page_data):
        """Check if page is a list or index page"""
        title = page_data.get('title', '').lower()
        
        # Common patterns for list/index pages
        list_patterns = [
            'list of',
            'index of',
            'timeline of',
            'glossary of',
            'outline of'
        ]
        
        return any(pattern in title for pattern in list_patterns)

    def get_candidate_pages(self, term, lang):
        """Get and rank candidate pages from Wikipedia search"""
        if not term:
            return []

        url = self.build_api_url(lang)
        params = {
            'origin': '*',
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': term,
            'srlimit': self.MAX_CANDIDATES,
            'srwhat': 'text',
            'utf8': 1,
        }

        response = requests.get(url, headers=self.get_headers(lang), params=params, timeout=10)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            logger.warning("Invalid response while searching Wikipedia for '%s'", term)
            return [{'title': term, 'pageid': None}]

        search_results = data.get('query', {}).get('search', [])
        if not search_results:
            return [{'title': term, 'pageid': None}]

        normalized = term.lower()
        ranked_results = []
        
        for result in search_results:
            title = (result.get('title') or '').strip()
            if not title:
                continue
            
            title_lower = title.lower()
            
            # Calculate multiple similarity metrics
            similarity = SequenceMatcher(None, normalized, title_lower).ratio()
            
            # Boost score for exact matches
            exact_match = int(title_lower == normalized)
            
            # Boost score for titles that start with the search term
            starts_with = int(title_lower.startswith(normalized))
            
            # Penalize disambiguation pages
            is_disambig = int('disambiguation' in title_lower or '(disambig' in title_lower)
            
            # Penalize list/index pages
            is_list = int(any(p in title_lower for p in ['list of', 'index of', 'timeline of']))
            
            score = result.get('score') or 0
            
            ranked_results.append({
                'title': title,
                'pageid': result.get('pageid'),
                'exact': exact_match,
                'starts_with': starts_with,
                'similarity': similarity,
                'score': score,
                'is_disambig': is_disambig,
                'is_list': is_list
            })

        if not ranked_results:
            return [{'title': term, 'pageid': None}]

        # Sort by: exact match > starts with > not disambiguation > not list > similarity > search score
        ranked_results.sort(
            key=lambda e: (
                e['exact'],
                e['starts_with'],
                -e['is_disambig'],
                -e['is_list'],
                e['similarity'],
                e['score']
            ),
            reverse=True
        )

        candidates = []
        seen_titles = set()
        
        for entry in ranked_results:
            title_key = entry['title'].lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            candidates.append({'title': entry['title'], 'pageid': entry['pageid']})
            if len(candidates) >= self.MAX_CANDIDATES:
                break

        # Add original term as fallback if not already included
        if normalized not in seen_titles:
            candidates.append({'title': term, 'pageid': None})

        return candidates

    def fetch_page(self, *, lang, candidate, props, extra_params=None):
        """Fetch page data from Wikipedia API"""
        if not candidate or not candidate.get('title'):
            return None

        params = {
            'origin': '*',
            'action': 'query',
            'format': 'json',
            'prop': props,
        }

        page_id = candidate.get('pageid')
        if page_id:
            params['pageids'] = page_id
        else:
            params['titles'] = candidate['title']

        if extra_params:
            params.update(extra_params)

        response = requests.get(
            self.build_api_url(lang),
            headers=self.get_headers(lang),
            params=params,
            timeout=10
        )
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            logger.warning("Invalid response while fetching Wikipedia page '%s'", candidate['title'])
            return None

        pages = data.get('query', {}).get('pages', {})
        if not pages:
            return None

        if page_id is not None:
            page_data = pages.get(str(page_id))
            if page_data:
                page_data.setdefault('title', candidate['title'])
                return page_data

        page_data = next(iter(pages.values()))
        if page_data:
            page_data.setdefault('title', candidate['title'])
        return page_data

    def get_language(self, request):
        """Extract and validate language parameter"""
        candidate = request.query_params.get('lang')
        if not candidate:
            candidate = self.DEFAULT_LANGUAGE

        if not candidate:
            candidate = 'en'

        normalized = candidate.replace('_', '-').lower()
        if self.LANGUAGE_PATTERN.match(normalized):
            return normalized

        return 'en'

    def get_headers(self, lang):
        """Build headers for Wikipedia API request"""
        headers = dict(self.BASE_HEADERS)
        headers['Accept-Language'] = lang
        headers['Accept'] = 'application/json'
        return headers

    def build_api_url(self, lang):
        """Build Wikipedia API URL for given language"""
        subdomain = lang.split('-', 1)[0]
        return f'https://{subdomain}.wikipedia.org/w/api.php'