import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchSecurityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test-only',
            'DATABASE': str(Path(self.tmp.name) / 'shop.db'),
        })
        self.client = self.app.test_client()

    def test_search_term_cannot_change_the_query_predicate(self):
        ordinary = self.client.get('/', query_string={'q': '咖啡'})
        self.assertIn('咖啡豆 500g', ordinary.text)

        response = self.client.get('/', query_string={'q': "' OR 1--"})
        self.assertLess(response.status_code, 500)
        self.assertNotIn('复古相机', response.text,
                         'SQL syntax changed the product search predicate')


if __name__ == '__main__':
    unittest.main()
