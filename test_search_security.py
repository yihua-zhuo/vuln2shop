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

    def test_search_input_cannot_change_the_query(self):
        response = self.client.get('/', query_string={'q': '咖啡'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('咖啡豆 500g', response.text)

        response = self.client.get('/', query_string={'q': "' --"})
        self.assertLess(response.status_code, 500)
        self.assertNotIn(
            '咖啡豆 500g', response.text,
            'Search input changed the SQL query and returned an unrelated product',
        )


if __name__ == '__main__':
    unittest.main()
