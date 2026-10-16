"""Search text must not become HTML in the public storefront."""

from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest

from app import create_app


class ElementCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.tags.append(tag)


class SearchHtmlSecurityTest(unittest.TestCase):
    def test_search_cannot_create_html_elements(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            with app.test_client() as client:
                ordinary = client.get('/', query_string={'q': '咖啡'})
                self.assertEqual(ordinary.status_code, 200)
                self.assertIn('咖啡豆', ordinary.get_data(as_text=True))

                # An inert custom element detects HTML interpretation without
                # scripts, event handlers, resource loads, or SQL metacharacters.
                response = client.get('/', query_string={'q': '<x-search-marker>'})
                self.assertIn(response.status_code, (200, 400, 422))
                document = ElementCollector()
                document.feed(response.get_data(as_text=True))
                self.assertNotIn(
                    'x-search-marker', document.tags,
                    'Search input was interpreted as an HTML element',
                )


if __name__ == '__main__':
    unittest.main()
