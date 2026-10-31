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
            db.execute(
                'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                ("Reader's quote-product-marker", "Reader's notebook.", 100),
            )

    def test_search_does_not_interpret_quotes_as_sql(self):
        response = self.client.get('/', query_string={'q': 'Reader'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('quote-product-marker', response.text)

        # Two literal apostrophes cannot match this product's single apostrophes.
        response = self.client.get('/', query_string={'q': "''"})
        self.assertLess(response.status_code, 500)
        self.assertNotIn(
            'quote-product-marker', response.text,
            'Search interpreted two apostrophes as SQL and returned a nonmatching product',
        )


if __name__ == '__main__':
    unittest.main()
