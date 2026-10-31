import sqlite3
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
        with sqlite3.connect(self.config['DATABASE']) as db:
            db.executemany(
                'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                [('single-quote-marker', "'", 100),
                 ('double-quote-marker', "''", 100)],
            )

    def test_search_quotes_cannot_change_selected_products(self):
        response = self.client.get('/', query_string={'q': 'double-quote-marker'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('double-quote-marker', response.text)
        self.assertNotIn('single-quote-marker', response.text)

        # Two apostrophes must stay search text, not become a SQL string escape.
        response = self.client.get('/', query_string={'q': "''"})
        self.assertIn(response.status_code, (200, 400, 422))
        self.assertNotIn(
            'single-quote-marker', response.text,
            'Search quotes changed SQL matching and exposed a nonmatching product',
        )


if __name__ == '__main__':
    unittest.main()
