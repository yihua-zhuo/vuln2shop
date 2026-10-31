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
                ('quote-regression-product', "A single apostrophe: '", 100),
            )

    def test_anonymous_search_does_not_interpret_sql_quotes(self):
        response = self.client.get('/', query_string={'q': 'quote'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('quote-regression-product', response.text)

        # SQL interpolation turns two apostrophes into one; literal search must not.
        response = self.client.get('/', query_string={'q': "''"})
        self.assertIn(response.status_code, (200, 400, 422))
        self.assertNotIn(
            'quote-regression-product', response.text,
            'Search treated doubled apostrophes as SQL instead of literal text',
        )


if __name__ == '__main__':
    unittest.main()
