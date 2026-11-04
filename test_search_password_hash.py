import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchPasswordHashTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = {'TESTING': True, 'SECRET_KEY': 'test-only',
                       'DATABASE': str(Path(self.tmp.name) / 'shop.db')}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.hash_marker = 'hash_probe_73'
        with sqlite3.connect(self.config['DATABASE']) as db:
            db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                       ('fixture-user', self.hash_marker))

    def test_anonymous_search_does_not_expose_password_hash(self):
        ordinary = self.client.get('/', query_string={'q': '咖啡'})
        self.assertIn('咖啡豆', ordinary.text)

        query = "%' UNION SELECT 5, username, password_hash, 0 FROM users -- "
        response = self.client.get('/', query_string={'q': query})
        self.assertNotIn(self.hash_marker, response.text,
                         'search exposed a stored password hash')


if __name__ == '__main__':
    unittest.main()
