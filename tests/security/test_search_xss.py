import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import create_app


class ElementParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


class SearchEscapingTest(unittest.TestCase):
    def test_search_query_does_not_create_html_elements(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'test-only',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            client = app.test_client()
            self.assertEqual(client.get('/').status_code, 200)

            # An inert, minimal tag detects HTML interpretation without scripts.
            response = client.get('/', query_string={'q': '<x>'})
            self.assertIn(response.status_code, (200, 400, 422))
            parser = ElementParser()
            parser.feed(response.get_data(as_text=True))
            parser.close()
            self.assertNotIn(
                'x', parser.tags,
                'The search query must not become an HTML element, including '
                'on an error page.',
            )
