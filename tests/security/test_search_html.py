import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import create_app


class ElementCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


class SearchHtmlSecurityTest(unittest.TestCase):
    def test_search_does_not_create_html_elements(self):
        with tempfile.TemporaryDirectory() as directory:
            client = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test',
                'DATABASE': str(Path(directory) / 'shop.db'),
            }).test_client()
            benign = client.get('/', query_string={'q': 'marker'})
            self.assertEqual(benign.status_code, 200)
            self.assertIn('marker', benign.text)
            baseline = ElementCollector()
            baseline.feed(benign.text)

            response = client.get('/', query_string={'q': '<b>marker</b>'})
            self.assertIn(response.status_code, (200, 400, 422))
            rendered = ElementCollector()
            rendered.feed(response.text)
            self.assertLessEqual(
                rendered.tags.count('b'), baseline.tags.count('b'),
                'Search input was interpreted as an HTML element',
            )
