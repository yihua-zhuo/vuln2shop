"""Regression coverage for HTML supplied through the public search query."""
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
    def test_search_does_not_interpret_query_as_html(self):
        with tempfile.TemporaryDirectory() as directory:
            client = create_app({
                'TESTING': True,
                'SECRET_KEY': 'security-test-only',
                'DATABASE': str(Path(directory) / 'shop.db'),
            }).test_client()

            ordinary = client.get('/', query_string={'q': '咖啡'})
            self.assertEqual(ordinary.status_code, 200)
            self.assertIn('咖啡豆', ordinary.get_data(as_text=True))

            # A formatting element is enough to detect unsafe HTML insertion;
            # no script, event handler, or external resource is needed.
            response = client.get('/', query_string={'q': '<b>marker</b>'})
            self.assertIn(response.status_code, (200, 400, 422))
            document = ElementCollector()
            document.feed(response.get_data(as_text=True))
            self.assertNotIn(
                'b', document.tags,
                'Search query was interpreted as HTML instead of text',
            )


if __name__ == '__main__':
    unittest.main()
