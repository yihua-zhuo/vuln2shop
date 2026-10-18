import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import create_app


class SearchMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


class SearchXssSecurityTest(unittest.TestCase):
    def test_search_query_cannot_create_html_elements(self):
        with tempfile.TemporaryDirectory() as directory:
            application = create_app({
                'TESTING': True,
                'SECRET_KEY': 'test-only',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            with application.test_client() as client:
                ordinary_response = client.get('/', query_string={'q': 'search-marker'})
                self.assertEqual(ordinary_response.status_code, 200)
                self.assertIn('search-marker', ordinary_response.get_data(as_text=True))

                response = client.get('/', query_string={'q': '<search-marker>'})
                self.assertIn(response.status_code, (200, 400, 403, 422))
                parser = SearchMarkupParser()
                parser.feed(response.get_data(as_text=True))
                parser.close()
                self.assertNotIn(
                    'search-marker', parser.tags,
                    'Search query markup must not become an HTML element',
                )
