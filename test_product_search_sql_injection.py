import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class ProductSearchSQLInjectionTest(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        database_path = Path(temporary_directory.name) / 'shop.db'
        application = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test-only',
            'DATABASE': str(database_path),
        })
        self.client = application.test_client()
        self.marker = 'SearchSecurityCanary'
        with sqlite3.connect(database_path) as database:
            database.execute(
                'INSERT INTO products (name, description, price_cents) VALUES (?, ?, ?)',
                (f"{self.marker} O'Brien", 'An ordinary test product.', 100),
            )

    def test_search_quotes_cannot_return_a_nonmatching_product(self):
        ordinary_response = self.client.get('/', query_string={'q': self.marker})
        self.assertEqual(ordinary_response.status_code, 200)
        self.assertIn(self.marker, ordinary_response.get_data(as_text=True))

        quote_response = self.client.get('/', query_string={'q': "''"})
        self.assertIn(quote_response.status_code, (200, 400, 403, 422))
        self.assertNotIn(
            self.marker,
            quote_response.get_data(as_text=True),
            'Search must not return a product that does not contain the literal search term',
        )


if __name__ == '__main__':
    unittest.main()
