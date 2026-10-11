"""Regression coverage for reflected script injection through storefront search."""

from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest

from app import create_app


class _ScriptCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.count += 1


class SearchXssSecurityTest(unittest.TestCase):
    def test_anonymous_search_cannot_create_script_elements(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test-only',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            client = app.test_client()
            baseline = client.get('/', query_string={'q': 'no-match-marker'})
            self.assertEqual(baseline.status_code, 200)
            baseline_html = _ScriptCounter()
            baseline_html.feed(baseline.get_data(as_text=True))
            baseline_html.close()

            # An empty script element contains no executable code or external URL.
            response = client.get(
                '/', query_string={'q': '<script></script>'}, follow_redirects=True,
            )
            self.assertTrue(
                response.status_code == 200 or 400 <= response.status_code < 500,
                f'Search must render safely or reject the input, got {response.status_code}',
            )
            search_html = _ScriptCounter()
            search_html.feed(response.get_data(as_text=True))
            search_html.close()
            self.assertLessEqual(
                search_html.count,
                baseline_html.count,
                'The search query created a script element; escape, remove, or reject its markup.',
            )


if __name__ == '__main__':
    unittest.main()
