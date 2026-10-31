import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchSecurityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = {'TESTING': True, 'SECRET_KEY': 'test-only',
                       'DATABASE': str(Path(self.tmp.name) / 'shop.db')}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def test_search_cannot_return_union_supplied_rows(self):
        response = self.client.get('/', query_string={'q': '咖啡'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('咖啡豆', response.text)

        # Split the marker so reflecting the search text cannot trip the check.
        query = "x' UNION SELECT 0,'search-'||'union-marker','',0 -- "
        response = self.client.get('/', query_string={'q': query})
        self.assertTrue(response.status_code == 200 or 400 <= response.status_code < 500,
                        'Search must handle SQL-looking input without a server error')
        self.assertNotIn('search-union-marker', response.text,
                         'Search must not render rows supplied by SQL syntax')


if __name__ == '__main__':
    unittest.main()
