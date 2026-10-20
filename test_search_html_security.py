"""Regression coverage for HTML injection through public search links."""

from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest

from app import create_app


class ElementCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


class SearchHtmlSecurityTest(unittest.TestCase):
    def test_search_term_cannot_create_html_elements(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            client = app.test_client()
            ordinary = client.get('/', query_string={'q': '咖啡'})
            self.assertEqual(ordinary.status_code, 200)
            self.assertIn('咖啡豆', ordinary.get_data(as_text=True))

            # An inert custom element distinguishes text from parsed markup
            # without running JavaScript or loading any resource.
            response = client.get('/', query_string={'q': '<x-marker>'})
            self.assertIn(response.status_code, (200, 400, 422))
            document = ElementCollector()
            document.feed(response.get_data(as_text=True))
            self.assertNotIn(
                'x-marker', document.tags,
                'Search input must not create HTML elements in the response',
            )


if __name__ == '__main__':
    unittest.main()
