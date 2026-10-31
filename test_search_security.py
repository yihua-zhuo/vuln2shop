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

    def test_search_cannot_turn_a_nonmatch_into_all_products(self):
        response = self.client.get('/', query_string={'q': '咖啡'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('咖啡豆 500g', response.text)

        response = self.client.get('/', query_string={'q': 'no-match'})
        self.assertIn('没有找到相关商品', response.text)

        response = self.client.get('/', query_string={'q': "no-match' OR 1 --"})
        self.assertTrue(response.status_code == 200 or 400 <= response.status_code < 500)
        self.assertNotIn(
            '复古相机', response.text,
            'Search syntax must not return unrelated products',
        )


if __name__ == '__main__':
    unittest.main()
