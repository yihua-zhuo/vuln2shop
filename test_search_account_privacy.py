import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchAccountPrivacyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = {'TESTING': True, 'SECRET_KEY': 'test-only',
                       'DATABASE': str(Path(self.tmp.name) / 'shop.db')}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.username = 'private-account-marker'
        self.password_hash = 'private-password-hash-marker'
        with sqlite3.connect(self.config['DATABASE']) as db:
            db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                       (self.username, self.password_hash))

    def test_anonymous_search_does_not_expose_account_data(self):
        response = self.client.get('/', query_string={'q': '咖啡'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('咖啡豆 500g', response.text)

        # Only synthetic account data exists in this temporary database.
        query = "no-match' UNION SELECT id,username,password_hash,0 FROM users-- "
        response = self.client.get('/', query_string={'q': query})
        self.assertLess(response.status_code, 500)
        self.assertNotIn(self.password_hash, response.text,
                         'Product search exposed a private account password hash')
        self.assertNotIn(self.username, response.text,
                         'Product search exposed a private account username')


if __name__ == '__main__':
    unittest.main()
