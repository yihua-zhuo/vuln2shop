import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import create_app


class ScriptCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.count += 1


class SearchXssSecurityTest(unittest.TestCase):
    def test_search_query_cannot_create_script_elements(self):
        with tempfile.TemporaryDirectory() as directory:
            application = create_app({
                'TESTING': True,
                'SECRET_KEY': 'search-security-test-only',
                'DATABASE': str(Path(directory) / 'shop.db'),
            })
            with application.test_client() as client:
                ordinary = client.get('/', query_string={'q': '咖啡'})
                self.assertEqual(ordinary.status_code, 200)
                self.assertIn('咖啡豆', ordinary.get_data(as_text=True))
                baseline = ScriptCounter()
                baseline.feed(ordinary.get_data(as_text=True))

                response = client.get('/', query_string={'q': '<script></script>'})
                self.assertIn(response.status_code, (200, 400, 422))
                rendered = ScriptCounter()
                rendered.feed(response.get_data(as_text=True))
                self.assertLessEqual(
                    rendered.count,
                    baseline.count,
                    'Search input created a script element in the HTML response',
                )


if __name__ == '__main__':
    unittest.main()
