"""Security regression coverage for the public storefront search."""

import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import create_app


class _ScriptCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.count += 1


def _script_count(response):
    if response.mimetype not in ('text/html', 'application/xhtml+xml'):
        return 0
    parser = _ScriptCounter()
    parser.feed(response.get_data(as_text=True))
    parser.close()
    return parser.count


class SearchXSSSecurityTest(unittest.TestCase):
    def test_search_text_cannot_create_script_elements(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            client = app.test_client()

            # Allow legitimate page scripts, including scripts on search pages.
            baseline = client.get('/', query_string={'q': 'probe'})
            self.assertEqual(baseline.status_code, 200)

            # An empty element contains no JavaScript or external resource.
            response = client.get(
                '/', query_string={'q': '<script></script>'},
                follow_redirects=True,
            )
            self.assertIn(response.status_code, (200, 400, 403, 422))
            self.assertLessEqual(
                _script_count(response), _script_count(baseline),
                'Search input created a script element; it must be escaped, '
                'removed, or rejected without reflecting executable markup.',
            )


if __name__ == '__main__':
    unittest.main()
