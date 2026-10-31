import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchSecurityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        database = str(Path(self.tmp.name) / 'shop.db')
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only',
                               'DATABASE': database})
        self.client = self.app.test_client()
        self.password_marker = 'private-account-marker'
        with sqlite3.connect(database) as db:
            db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                       ('search-test-user', self.password_marker))

    def test_search_does_not_expose_account_passwords(self):
        response = self.client.get('/', query_string={'q': '咖啡'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('咖啡豆', response.text)

        query = "' UNION SELECT 0,password_hash,'',0 FROM users-- "
        response = self.client.get('/', query_string={'q': query})
        self.assertLess(response.status_code, 500)
        self.assertNotIn(self.password_marker, response.text,
                         'Product search exposed an account password marker')


if __name__ == '__main__':
    unittest.main()
