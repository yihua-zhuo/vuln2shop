"""Security regression coverage for reflected HTML in storefront searches."""

import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import create_app


class _ScriptElements(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.count = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.count += 1


class SearchXssSecurityTest(unittest.TestCase):
    def test_search_input_cannot_create_script_elements(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test-only',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            with app.test_client() as client:
                baseline = client.get('/', query_string={'q': 'marker'})
                self.assertEqual(baseline.status_code, 200)

                # An empty element contains no JavaScript or external resources.
                response = client.get(
                    '/', query_string={'q': '<script></script>'},
                    follow_redirects=True,
                )
                self.assertIn(response.status_code, (200, 400, 403, 422))

                baseline_elements = _ScriptElements()
                baseline_elements.feed(baseline.get_data(as_text=True))
                baseline_elements.close()
                search_elements = _ScriptElements()
                search_elements.feed(response.get_data(as_text=True))
                search_elements.close()

                self.assertLessEqual(
                    search_elements.count,
                    baseline_elements.count,
                    'The search query created a script element in the returned HTML; '
                    'untrusted query text must be escaped, sanitized, or rejected.',
                )


if __name__ == '__main__':
    unittest.main()
