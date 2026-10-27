import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchAccountIsolationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = {'TESTING': True, 'SECRET_KEY': 'test-only',
                       'DATABASE': str(Path(self.tmp.name) / 'shop.db')}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.username = 'private-account-marker'
        self.password_hash = 'private-hash-marker'
        # This deliberately non-credential value only marks a private database field.
        with sqlite3.connect(self.config['DATABASE']) as db:
            db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                       (self.username, self.password_hash))

    def test_product_search_does_not_disclose_account_fields(self):
        response = self.client.get('/', query_string={'q': '咖啡'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('咖啡豆 500g', response.text)

        response = self.client.get('/', query_string={
            'q': "no-match' UNION SELECT id, username, password_hash, 0 FROM users --",
        })
        self.assertIn(response.status_code, (200, 400, 403, 422))
        self.assertNotIn(self.username, response.text,
                         'Product search disclosed a private account username')
        self.assertNotIn(self.password_hash, response.text,
                         'Product search disclosed a private password hash')


if __name__ == '__main__':
    unittest.main()
