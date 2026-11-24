from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase

from adventures.providers.wikipedia import fetch_summary
from adventures.providers.wikipedia import WikipediaClient, is_valid_image_url

LONG_EXTRACT = 'Paris is the capital and most populous city of France. ' * 3


def _response(status=200, payload=None):
    response = MagicMock(status_code=status)
    response.json.return_value = payload if payload is not None else {}
    response.raise_for_status.return_value = None
    return response


class FetchSummaryTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_empty_query_is_an_error_without_a_request(self):
        with patch('requests.get') as get:
            result = fetch_summary('   ')

        self.assertEqual(result.error, 'Missing query')
        get.assert_not_called()

    def test_returns_the_extract_and_encodes_the_title_and_language(self):
        with patch('requests.get', return_value=_response(payload={'extract': LONG_EXTRACT})) as get:
            result = fetch_summary('Paris, France', language=' EN ')

        self.assertEqual(result.data, LONG_EXTRACT.strip())
        self.assertEqual(
            get.call_args.args[0], 'https://en.wikipedia.org/api/rest_v1/page/summary/Paris%2C%20France'
        )
        self.assertEqual(get.call_args.kwargs['headers'], {'User-Agent': 'AdventureLog Server'})
        self.assertEqual(get.call_args.kwargs['timeout'], (2, 5))

    def test_a_regional_language_tag_uses_the_primary_language_site(self):
        for tag, host in (('pt-br', 'pt'), ('zh-hans', 'zh'), ('en-GB', 'en'), ('fr', 'fr')):
            with self.subTest(tag=tag):
                cache.clear()
                with patch('requests.get', return_value=_response(payload={'extract': LONG_EXTRACT})) as get:
                    result = fetch_summary('Lisboa', language=tag)
                self.assertEqual(result.data, LONG_EXTRACT.strip())
                self.assertTrue(get.call_args.args[0].startswith(f'https://{host}.wikipedia.org/'))

    def test_falls_back_to_the_part_before_the_first_comma(self):
        responses = [_response(status=404), _response(payload={'extract': LONG_EXTRACT})]
        with patch('requests.get', side_effect=responses) as get:
            result = fetch_summary('Paris, France')

        self.assertEqual(result.data, LONG_EXTRACT.strip())
        self.assertTrue(get.call_args.args[0].endswith('/Paris'))

    def test_disambiguation_and_short_extracts_are_skipped(self):
        responses = [
            _response(payload={'type': 'disambiguation', 'extract': LONG_EXTRACT}),
            _response(payload={'extract': 'Too short.'}),
        ]
        with patch('requests.get', side_effect=responses):
            result = fetch_summary('Paris, France')

        self.assertIsNone(result.data)
        self.assertIsNone(result.error)

    def test_request_errors_are_swallowed(self):
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError):
            result = fetch_summary('Paris')

        self.assertIsNone(result.data)
        self.assertIsNone(result.error)

    def test_a_found_summary_is_cached(self):
        with patch('requests.get', return_value=_response(payload={'extract': LONG_EXTRACT})) as get:
            fetch_summary('Paris')
            fetch_summary('Paris')

        self.assertEqual(get.call_count, 1)


class WikipediaClientTests(SimpleTestCase):
    def setUp(self):
        self.client_under_test = WikipediaClient()

    def test_api_host_uses_only_the_primary_language_subtag(self):
        self.assertEqual(self.client_under_test.build_api_url('pt-br'), 'https://pt.wikipedia.org/w/api.php')
        self.assertEqual(self.client_under_test.build_api_url('en'), 'https://en.wikipedia.org/w/api.php')

    def test_headers_carry_the_requested_language(self):
        headers = self.client_under_test.get_headers('fr')
        self.assertEqual(headers['Accept-Language'], 'fr')
        self.assertEqual(headers['Accept'], 'application/json')
        self.assertTrue(headers['User-Agent'].startswith('AdventureLog/'))

    def test_no_term_means_no_candidates_and_no_request(self):
        with patch('requests.get') as get:
            self.assertEqual(self.client_under_test.get_candidate_pages('', 'en'), [])
        get.assert_not_called()

    def test_no_search_hits_falls_back_to_the_term_itself(self):
        with patch('requests.get', return_value=_response(payload={'query': {'search': []}})):
            result = self.client_under_test.get_candidate_pages('Atlantis', 'en')

        self.assertEqual(result, [{'title': 'Atlantis', 'pageid': None}])

    def test_candidates_are_ranked_exact_first_then_non_lists_and_deduped(self):
        hits = [
            {'title': 'List of things named Paris', 'pageid': 1, 'score': 99},
            {'title': 'Paris (disambiguation)', 'pageid': 2, 'score': 50},
            {'title': 'Paris Hilton', 'pageid': 3, 'score': 10},
            {'title': 'Paris', 'pageid': 4, 'score': 1},
            {'title': 'paris', 'pageid': 5, 'score': 1},
        ]
        with patch('requests.get', return_value=_response(payload={'query': {'search': hits}})):
            result = self.client_under_test.get_candidate_pages('Paris', 'en')

        titles = [candidate['title'] for candidate in result]
        self.assertEqual(titles[0], 'Paris')
        self.assertEqual(len([t for t in titles if t.lower() == 'paris']), 1)
        self.assertLess(titles.index('Paris Hilton'), titles.index('Paris (disambiguation)'))
        self.assertLess(titles.index('Paris (disambiguation)'), titles.index('List of things named Paris'))

    def test_fetch_page_addresses_by_pageid_when_known_else_by_title(self):
        page = {'1': {'pageid': 1, 'extract': 'x'}}
        with patch('requests.get', return_value=_response(payload={'query': {'pages': page}})) as get:
            result = self.client_under_test.fetch_page(
                'en', {'title': 'Paris', 'pageid': 1}, 'extracts', {'exintro': 1}
            )
        params = get.call_args.kwargs['params']
        self.assertEqual((params['pageids'], params['prop'], params['exintro']), (1, 'extracts', 1))
        self.assertNotIn('titles', params)
        self.assertEqual(result['title'], 'Paris')

        with patch('requests.get', return_value=_response(payload={'query': {'pages': page}})) as get:
            self.client_under_test.fetch_page('en', {'title': 'Paris', 'pageid': None}, 'extracts')
        self.assertEqual(get.call_args.kwargs['params']['titles'], 'Paris')

    def test_fetch_page_without_a_title_does_nothing(self):
        with patch('requests.get') as get:
            self.assertIsNone(self.client_under_test.fetch_page('en', {'pageid': 1}, 'extracts'))
        get.assert_not_called()

    def test_image_url_validation(self):
        self.assertTrue(is_valid_image_url('https://upload.wikimedia.org/a/b/photo.JPG'))
        self.assertFalse(is_valid_image_url('https://upload.wikimedia.org/a/b/map.svg'))
        self.assertFalse(is_valid_image_url('https://example.com/readme.txt'))
        self.assertFalse(is_valid_image_url(None))
